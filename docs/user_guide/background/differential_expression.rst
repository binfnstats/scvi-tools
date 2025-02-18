==============================
Differential Expression
==============================

Under construction.

Problem statement
==========================================

Differential expression analyses aim to quantify and detect expression differences of some quantity between conditions, e.g., cell types.
In single-cell experiments, such quantity can correspond to transcripts, protein expression, or chromatin accessibility.
A central notion when comparing expression levels of two cell states 
is the log fold-change

.. math::
   :nowrap:

   \begin{align}
      \beta_g := \log h_{g}^B - \log h_{g}^A,
   \end{align}

where 
:math:`\log h_{g}^A, \log h_{g}^B`
respectively denote the mean expression levels in subpopulations :math:`A`
and
:math:`B`.



Motivations to use scVI-tools for differential expression 
======================================================================

In the particular case of single-cell RNA-seq data, existing differential expression models often model that the mean expression level 
:math:`\log h_{g}^C`.
as a linear function of the cell-state and batch assignments.
These models face two notable limitations to detect differences in expression between cell-states in large-scale scRNA-seq datasets.
First, such linear assumptions may not capture complex batch effects existing in such datasets accurately.
When comparing two given states :math:`A`
and
:math:`B` in a large dataset, these models may also struggle to leverage data of a related state present in the data.

Deep generative models may not suffer from these problems.
Most ``scvi-tools`` models use complex nonlinear mappings to capture batch effects on expression.
Using amortization, they can leverage large amounts of data
to better capture shared correlations between features.
Consequently, deep generative models have appealing properties for differential expression in large-scale data.

This guide has two objectives.
First, it aims to provide insight as to how scVI-tools' differential expression module works for transcript expression (``scVI``), surface protein expression (``TOTALVI``), or chromatin accessibility (``PeakVI``).
More precisely, we explain how it can:

    + approximate population-specific normalized expression levels

    + detect biologically relevant features

    + provide easy-to-interpret predictions

More importantly, this guide explains the function of the hyperparameters of the ``differential_expression`` method.


.. list-table::
   :widths: 20 50 15 15 15
   :header-rows: 1

   * - Parameter
     - Description
     - Approximating expression levels
     - Detecting relevant features
     - Providing easy-to-interpret predictions
   * - ``idx1``, ``idx2``
     - Mask or queries for the compared populations :math:`A` and :math:`B`.
     - yes
     - 
     - 
   * - ``mode``
     - Characterizes the null hypothesis.
     - 
     - yes
     - 
   * - ``delta``
     - composite hypothesis characteristics (when ``mode="change"``).
     - 
     - yes
     - 
   * - ``fdr_target``
     - desired FDR significance level
     - 
     - 
     - yes
   * - ``importance_sampling``
     - Precises if expression levels are estimated using importance sampling
     - yes
     - 
     - 

Notations and model assumptions
======================================================================
While considering different modalities, scVI, TOTALVI, and PeakVI share similar properties, allowing us to perform differential expression of transcripts, surface proteins, or chromatin accessibility, similarly.
We first introduce some notations that will be useful in the remainder of this guide.
In particular, we consider a deep generative model where a latent variable with prior :math:`z_n \sim \mathcal{N}_d(0, I_d)` represents cell :math:`n`'s identity.
In turn, a neural network :math:`f^h_\theta` maps this low-dimensional representation to normalized, expression levels.
The following table recaps which names the scVI-tools codebase uses.

.. list-table::
   :widths: 20 50 15 15
   :header-rows: 1

   * - Model
     - Type of expression
     - latent variable name
     - Normaled expression name
   * - scVI
     - Gene expression.
     - ``z``
     - ``px_scale``
   * - TOTALVI
     - Gene & surface protein expression.
     - ``z``
     - ``px_scale`` (gene) and ``py_scale`` (surface protein)
   * - PEAKVI
     - Chromatin accessibility.
     - ``z``
     - ``p``


Approximating population-specific normalized expression levels
====================================================================================

A first step to characterize differences in expression consists in estimating state-specific expression levels.
For several reasons, most ``scVI-tools`` models do not explicitly model discrete cell types. 
A given cell's state often is unknown in the first place, and inferred with ``scvi-tools``.
In some cases, states may also have an intricate structure that would be difficult to model.
The class of models we consider here assumes that a latent variable :math:`z` characterizes cells' biological identity.
A key component of our differential expression module is to aggregate the information carried by individual cells to estimate population-wide expression levels.
The strategy to do so is as follows.
First, we estimate latent representations of the two compared states :math:`A` and :math:`B`, using aggregate variational posteriors.
In particular, we will represent state :math:`C` latent representation with the mixture

.. math::
   :nowrap:

   \begin{align}
      \hat P^C(
        Z
      ) = 
      \frac
      {1}
      {
        \mathcal{N}_C
      }
      \sum_{n \in \mathcal{N}_C}
      p_\theta(z \mid x_n),
   \end{align}

where ``idx1`` and``idx2`` specify which observations to use to approximate these quantities.

Once established latent distributions for each state, expression vectors :math:`h_{n} \in \mathbb{R}^F` (:math:`F` being the total number of features) are obtained as neural network outputs :math:`h_n = f^h_\theta(z_n)`.
We note :math:`h^A_f, h^B_f` the respective expression levels in states :math:`A, B` obtained using this sampling procedure.




Detecting biologically relevant features
========================================================
Once we have expression levels distributions for each condition, scvi-tools constructs an effect size, which will characterize expression differences.
When considering gene or surface protein expression, log-normalized counts are a traditional choice to characterize expression levels.
. Consequently, the canonical effect size for feature :math:`f` is the log fold-change, defined as the difference between log expression between conditions,

.. math::
   :nowrap:

   \begin{align}
      \beta_f
      = 
      \log_2 h_^B{f} - \log_2 h_^A{f}.
   \end{align}
As chromatin accessibility cannot be interpreted in the same way, we take :math:`\beta_f = h_^B{f}- h_^A{f}` instead.

scVI-tools provides several ways to formulate the competing hypotheses from the effect sizes to detect DE features.
When ``mode = "vanilla"``, we consider point null hypotheses of the form :math:`\mathcal{H}_{0f}: \beta_f = 0`.
To avoid detecting features of little practical interest, e.g., when expression differences between conditions are significant but very subtle, we recommend users to use ``mode = "change"`` instead.
In this formulation, we consider null hypotheses instead, such that 

.. math::
   :nowrap:

   \begin{align}
      \lvert \beta_f \rvert
      \leq 
      \delta.
   \end{align}

Here, :math:`\delta` is an hyperparameter specified by ``delta``.
Note that when ``delta=None``, we estimate this parameter in a data-driven fashion.
A straightforward decision consists in detecting genes for which the posterior distribution of the event :math:`\lvert \beta_f \rvert \leq \delta`, that we denote :math:`p_f`, is above a threshold :math:`1 - \epsilon`.


Providing easy-to-interpret predictions
========================================================
The obtained gene sets may be difficult to interpret for some users.
For this reason, we provide a data-supported way to select :math:`\epsilon`, such that the posterior expected False Discovery Proportion (FDP) is below a significance level :math:`\alpha`.
To clarify how to compute the posterior expectation, we introduce two notations.
We denote

.. math::
   :nowrap:

   \begin{align}
      \mu^k_f
      =
      \begin{cases}
        1 ~~\textrm{if feature $g$ is tagged DE} \\
        0 ~~\textrm{otherwise}
      \end{cases},
   \end{align}
the decision rule tagging :math:`k` features of highest :math:`p_f` as DE.
We also note :math:`d^f` the binary random variable taking value 1 if feature :math:`f` is differentially expressed.

The False Discovery Proportion is a random variable corresponding to the ratio of the number of false positives over the total number of predicted positives.
For the specific family of decision rules :math:`\mu^k, k` that we consider here, the FDP can be written as 

.. math::
   :nowrap:

   \begin{align}
      FDP_{\mu^k}
      =
      \frac
      {\sum_f (1 - d^f) \mu_f^k}
      {\sum_f \mu_f^k}
      .
   \end{align}
  
However, note that the posterior expectation of :math:`d^f`, denoted as :math:`\mathbb{E}_{post}[]`, verifies :math:`\mathbb{E}_{post}[FDP_{d^f}] = p^f`.
Hence, by linearity of the expectation, we can estimate the false discovery rate corresponding to :math:`k` detected features as 

.. math::
   :nowrap:

   \begin{align}
      \mathbb{E}_{post}[FDP_{\mu^k}]
      =
      \frac
      {\sum_f (1 - p^f) \mu_f^k}
      {\sum_f \mu_f^k}
      .
   \end{align}

 Hence, for a given significance level :math:`\alpha`, we select the maximum detections :math:`k^*`, such that :math:`\mathbb{E}_{post}[FDP_{\mu^k}] \leq \alpha`, as illustrated below.


 .. figure:: figures/fdr_control.png
   :class: img-fluid
   :align: center
   :alt: FDR control


