import logging
from typing import Dict, Optional, Sequence, Union

import numpy as np
import torch
from anndata import AnnData
from torch import logsumexp
from torch.distributions import Beta, Normal

from scvi import _CONSTANTS
from scvi._compat import Literal
from scvi.model._utils import _init_library_size
from scvi.model.base import UnsupervisedTrainingMixin
from scvi.module import AutoZIVAE

from .base import BaseModelClass, VAEMixin

logger = logging.getLogger(__name__)

# register buffer


class AUTOZI(VAEMixin, UnsupervisedTrainingMixin, BaseModelClass):
    """
    Automatic identification of ZI genes [Clivio19]_.

    Parameters
    ----------
    adata
        AnnData object that has been registered via :func:`~scvi.data.setup_anndata`.
    n_hidden
        Number of nodes per hidden layer
    n_latent
        Dimensionality of the latent space
    n_layers
        Number of hidden layers used for encoder NN
    dropout_rate
        Dropout rate for neural networks
    dispersion
        One of the following

        * ``'gene'`` - dispersion parameter of NB is constant per gene across cells
        * ``'gene-batch'`` - dispersion can differ between different batches
        * ``'gene-label'`` - dispersion can differ between different labels
        * ``'gene-cell'`` - dispersion can differ for every gene in every cell
    latent_distribution
        One of

        * ``'normal'`` - Normal distribution
        * ``'ln'`` - Logistic normal distribution (Normal(0, I) transformed by softmax)
    alpha_prior
        Float denoting the alpha parameter of the prior Beta distribution of
        the zero-inflation Bernoulli parameter. Should be between 0 and 1, not included.
        When set to ``None'', will be set to 1 - beta_prior if beta_prior is not ``None'',
        otherwise the prior Beta distribution will be learned on an Empirical Bayes fashion.
    beta_prior
        Float denoting the beta parameter of the prior Beta distribution of
        the zero-inflation Bernoulli parameter. Should be between 0 and 1, not included.
        When set to ``None'', will be set to 1 - alpha_prior if alpha_prior is not ``None'',
        otherwise the prior Beta distribution will be learned on an Empirical Bayes fashion.
    minimal_dropout
        Float denoting the lower bound of the cell-gene ZI rate in the ZINB component.
        Must be non-negative. Can be set to 0 but not recommended as this may make
        the mixture problem ill-defined.
    zero_inflation: One of the following

        * ``'gene'`` - zero-inflation Bernoulli parameter of AutoZI is constant per gene across cells
        * ``'gene-batch'`` - zero-inflation Bernoulli parameter can differ between different batches
        * ``'gene-label'`` - zero-inflation Bernoulli parameter can differ between different labels
        * ``'gene-cell'`` - zero-inflation Bernoulli parameter can differ for every gene in every cell
    use_observed_lib_size
        Use observed library size for RNA as scaling factor in mean of conditional distribution
    **model_kwargs
        Keyword args for :class:`~scvi.module.AutoZIVAE`

    Examples
    --------

    >>> adata = anndata.read_h5ad(path_to_anndata)
    >>> scvi.data.setup_anndata(adata, batch_key="batch")
    >>> vae = scvi.model.AutoZIVAE(adata)
    >>> vae.train(n_epochs=400)

    Notes
    -----
    See further usage examples in the following tutorials:

    1. :doc:`/user_guide/notebooks/AutoZI_tutorial`
    """

    def __init__(
        self,
        adata: AnnData,
        n_hidden: int = 128,
        n_latent: int = 10,
        n_layers: int = 1,
        dropout_rate: float = 0.1,
        dispersion: Literal["gene", "gene-batch", "gene-label", "gene-cell"] = "gene",
        latent_distribution: Literal["normal", "ln"] = "normal",
        alpha_prior: Optional[float] = 0.5,
        beta_prior: Optional[float] = 0.5,
        minimal_dropout: float = 0.01,
        zero_inflation: str = "gene",
        use_observed_lib_size: bool = True,
        **model_kwargs,
    ):
        super(AUTOZI, self).__init__(adata)

        self.use_observed_lib_size = use_observed_lib_size
        n_batch = self.summary_stats["n_batch"]
        library_log_means, library_log_vars = _init_library_size(adata, n_batch)

        self.module = AutoZIVAE(
            n_input=self.summary_stats["n_vars"],
            n_batch=n_batch,
            n_labels=self.summary_stats["n_labels"],
            n_hidden=n_hidden,
            n_latent=n_latent,
            n_layers=n_layers,
            dropout_rate=dropout_rate,
            dispersion=dispersion,
            latent_distribution=latent_distribution,
            zero_inflation=zero_inflation,
            alpha_prior=alpha_prior,
            beta_prior=beta_prior,
            minimal_dropout=minimal_dropout,
            use_observed_lib_size=use_observed_lib_size,
            library_log_means=library_log_means,
            library_log_vars=library_log_vars,
            **model_kwargs,
        )
        self.model_summary_string = (
            "AutoZI Model with the following params: \nn_hidden: {}, n_latent: {}, "
            "n_layers: {}, dropout_rate: {}, dispersion: {}, latent_distribution: "
            "{}, alpha_prior: {}, beta_prior: {}, minimal_dropout: {}, zero_inflation:{}"
        ).format(
            n_hidden,
            n_latent,
            n_layers,
            dropout_rate,
            dispersion,
            latent_distribution,
            alpha_prior,
            beta_prior,
            minimal_dropout,
            zero_inflation,
        )
        self.init_params_ = self._get_init_params(locals())

    def get_alphas_betas(
        self, as_numpy: bool = True
    ) -> Dict[str, Union[torch.Tensor, np.ndarray]]:
        """Return parameters of Bernoulli Beta distributions in a dictionary."""
        return self.module.get_alphas_betas(as_numpy=as_numpy)

    @torch.no_grad()
    def get_marginal_ll(
        self,
        adata: Optional[AnnData] = None,
        indices: Optional[Sequence[int]] = None,
        n_mc_samples: int = 1000,
        batch_size: Optional[int] = None,
    ) -> float:
        """
        Return the marginal LL for the data.

        The computation here is a biased estimator of the marginal log likelihood of the data.
        Note, this is not the negative log likelihood, higher is better.

        Parameters
        ----------
        adata
            AnnData object with equivalent structure to initial AnnData. If `None`, defaults to the
            AnnData object used to initialize the model.
        indices
            Indices of cells in adata to use. If `None`, all cells are used.
        n_mc_samples
            Number of Monte Carlo samples to use for marginal LL estimation.
        batch_size
            Minibatch size for data loading into model. Defaults to `scvi.settings.batch_size`.
        """
        adata = self._validate_anndata(adata)
        if indices is None:
            indices = np.arange(adata.n_obs)

        scdl = self._make_data_loader(
            adata=adata, indices=indices, batch_size=batch_size
        )

        log_lkl = 0
        to_sum = torch.zeros((n_mc_samples,)).to(self.device)
        alphas_betas = self.module.get_alphas_betas(as_numpy=False)
        alpha_prior = alphas_betas["alpha_prior"]
        alpha_posterior = alphas_betas["alpha_posterior"]
        beta_prior = alphas_betas["beta_prior"]
        beta_posterior = alphas_betas["beta_posterior"]

        for i in range(n_mc_samples):
            bernoulli_params = self.module.sample_from_beta_distribution(
                alpha_posterior, beta_posterior
            )
            for tensors in scdl:
                sample_batch = tensors[_CONSTANTS.X_KEY].to(self.device)
                batch_index = tensors[_CONSTANTS.BATCH_KEY].to(self.device)
                labels = tensors[_CONSTANTS.LABELS_KEY].to(self.device)

                # Distribution parameters and sampled variables
                inf_outputs, gen_outputs, _ = self.module.forward(tensors)

                px_r = gen_outputs["px_r"]
                px_rate = gen_outputs["px_rate"]
                px_dropout = gen_outputs["px_dropout"]
                qz_m = inf_outputs["qz_m"]
                qz_v = inf_outputs["qz_v"]
                z = inf_outputs["z"]
                library = inf_outputs["library"]

                # Reconstruction Loss
                bernoulli_params_batch = self.module.reshape_bernoulli(
                    bernoulli_params,
                    batch_index,
                    labels,
                )
                reconst_loss = self.module.get_reconstruction_loss(
                    sample_batch,
                    px_rate,
                    px_r,
                    px_dropout,
                    bernoulli_params_batch,
                )

                # Log-probabilities
                log_prob_sum = torch.zeros(qz_m.shape[0]).to(self.device)
                p_z = (
                    Normal(torch.zeros_like(qz_m), torch.ones_like(qz_v))
                    .log_prob(z)
                    .sum(dim=-1)
                )
                p_x_zld = -reconst_loss
                log_prob_sum += p_z + p_x_zld

                q_z_x = Normal(qz_m, qz_v.sqrt()).log_prob(z).sum(dim=-1)
                log_prob_sum -= q_z_x

                if not self.use_observed_lib_size:
                    (
                        local_library_log_means,
                        local_library_log_vars,
                    ) = self.module._compute_local_library_params(batch_index)

                    p_l = (
                        Normal(
                            local_library_log_means.to(self.device),
                            local_library_log_vars.to(self.device).sqrt(),
                        )
                        .log_prob(library)
                        .sum(dim=-1)
                    )

                    ql_m = inf_outputs["ql_m"]
                    ql_v = inf_outputs["ql_v"]
                    q_l_x = Normal(ql_m, ql_v.sqrt()).log_prob(library).sum(dim=-1)

                    log_prob_sum += p_l - q_l_x

                batch_log_lkl = torch.sum(log_prob_sum, dim=0)
                to_sum[i] += batch_log_lkl

            p_d = Beta(alpha_prior, beta_prior).log_prob(bernoulli_params).sum()
            q_d = Beta(alpha_posterior, beta_posterior).log_prob(bernoulli_params).sum()

            to_sum[i] += p_d - q_d

        log_lkl = logsumexp(to_sum, dim=-1).item() - np.log(n_mc_samples)
        n_samples = len(scdl.indices)
        return log_lkl / n_samples
