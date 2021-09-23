from docrep import DocstringProcessor

doc_differential_expression = """\
adata
    AnnData object with equivalent structure to initial AnnData.
    If None, defaults to the AnnData object used to initialize the model.
groupby
    The key of the observations grouping to consider.
group1
    Subset of groups, e.g. [`'g1'`, `'g2'`, `'g3'`], to which comparison
    shall be restricted, or all groups in `groupby` (default).
group2
    If `None`, compare each group in `group1` to the union of the rest of the groups
    in `groupby`. If a group identifier, compare with respect to this group.
idx1
    `idx1` and `idx2` can be used as an alternative to the AnnData keys.
    Custom identifier for `group1` that can be of three sorts: (1) a boolean mask,
    (2) indices, or (3) a string. If it is a string, then it will query indices that
    verifies conditions on `adata.obs`, as described in :meth:`pandas.DataFrame.query`
    If `idx1` is not `None`, this option overrides `group1`
    and `group2`.
idx2
    Custom identifier for `group2` that has the same
    properties as `idx1`.
    By default, includes all cells not specified in
    `idx1`.
mode
    Method for differential expression. See user guide for full explanation.
delta
    specific case of region inducing differential expression.
    In this case, we suppose that :math:`R \setminus [-\delta, \delta]` does not induce differential expression
    (change model default case).
batch_size
    Minibatch size for data loading into model. Defaults to `scvi.settings.batch_size`.
all_stats
    Concatenate count statistics (e.g., mean expression group 1) to DE results.
batch_correction
    Whether to correct for batch effects in DE inference.
batchid1
    Subset of categories from `batch_key` registered in ``setup_anndata``,
    e.g. [`'batch1'`, `'batch2'`, `'batch3'`], for `group1`. Only used if `batch_correction` is `True`, and
    by default all categories are used.
batchid2
    Same as `batchid1` for group2. `batchid2` must either have null intersection with `batchid1`,
    or be exactly equal to `batchid1`. When the two sets are exactly equal, cells are compared by
    decoding on the same batch. When sets have null intersection, cells from `group1` and `group2`
    are decoded on each group in `group1` and `group2`, respectively.
fdr_target
    Tag features as DE based on posterior expected false discovery rate.
silent
    If True, disables the progress bar. Default: False.
"""

setup_anndata_summary = """\
Sets up the :class:`~anndata.AnnData` object for this model.
A mapping will be created between data fields used by this model to their respective locations in adata.

None of the data in adata are modified. Only adds fields to adata."""

setup_anndata_param_adata = """\
adata
    AnnData object containing raw counts. Rows represent cells, columns represent features."""

setup_anndata_param_batch_key = """\
batch_key
    key in `adata.obs` for batch information. Categories will automatically be converted into integer
    categories and saved to `adata.obs['_scvi_batch']`. If `None`, assigns the same batch to all the data."""

setup_anndata_param_labels_key = """\
labels_key
    key in `adata.obs` for label information. Categories will automatically be converted into integer
    categories and saved to `adata.obs['_scvi_labels']`. If `None`, assigns the same label to all the data."""

setup_anndata_param_layer = """\
layer
    if not `None`, uses this as the key in `adata.layers` for raw count data."""

setup_anndata_param_cat_cov_keys = """\
categorical_covariate_keys
    keys in `adata.obs` that correspond to categorical data."""

setup_anndata_param_cont_cov_keys = """\
continuous_covariate_keys
    keys in `adata.obs` that correspond to continuous data."""

setup_anndata_param_copy = """\
copy
    if `True`, a copy of adata is returned."""

setup_anndata_returns = """\
If ``copy``,  will return :class:`~anndata.AnnData`.
Adds the following fields to adata:

.uns['_scvi']
    `scvi` setup dictionary
.obs['_scvi_labels']
    labels encoded as integers
.obs['_scvi_batch']
    batch encoded as integers"""

dsp = DocstringProcessor(
    setup_anndata_summary=setup_anndata_summary,
    setup_anndata_param_adata=setup_anndata_param_adata,
    setup_anndata_param_batch_key=setup_anndata_param_batch_key,
    setup_anndata_param_labels_key=setup_anndata_param_labels_key,
    setup_anndata_param_layer=setup_anndata_param_layer,
    setup_anndata_param_cat_cov_keys=setup_anndata_param_cat_cov_keys,
    setup_anndata_param_cont_cov_keys=setup_anndata_param_cont_cov_keys,
    setup_anndata_param_copy=setup_anndata_param_copy,
    setup_anndata_returns=setup_anndata_returns,
)
