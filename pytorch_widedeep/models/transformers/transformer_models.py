import torch
from torch import nn

from pytorch_widedeep.wdtypes import *  # noqa: F403
from pytorch_widedeep.models.tab_mlp import MLP
from pytorch_widedeep.models.transformers.layers import (
    SaintEncoder,
    SharedEmbeddings,
    TransformerEncoder,
    FullEmbeddingDropout,
)


class TabTransformer(nn.Module):
    r"""Adaptation of TabTransformer model
    (https://arxiv.org/pdf/2012.06678.pdf) model that can be used as the
    deeptabular component of a Wide & Deep model.

    Parameters
    ----------
    column_idx: Dict
        Dict containing the index of the columns that will be passed through
        the DeepDense model. Required to slice the tensors. e.g. {'education':
        0, 'relationship': 1, 'workclass': 2, ...}
    embed_input: List
        List of Tuples with the column name and number of unique values
        e.g. [(education, 11), ...]
    continuous_cols: List, Optional, default = None
        List with the name of the numeric (aka continuous) columns
    embed_dropout: float, default = 0.1
        Dropout to be applied to the embeddings matrix
    full_embed_dropout: bool, default = False
        Boolean indicating if an entire embedding (i.e. the representation
        for one categorical column) will be dropped in the batch. See:
        :obj:`pytorch_widedeep.model.tab_transformer.FullEmbeddingDropout`.
        If ``full_embed_dropout = True``, ``embed_dropout`` is ignored.
    shared_embed: bool, default = False
        The idea behind ``shared_embed`` is described in the Appendix A in the paper:
        `'The goal of having column embedding is to enable the model to distinguish the
        classes in one column from those in the other columns'`. In other words, the idea
        is to let the model learn which column is embedding at the time.
    add_shared_embed: bool, default = False,
        The two embedding sharing strategies are: 1) add the shared embeddings to the column
        embeddings or 2) to replace the first ``frac_shared_embed`` with the shared
        embeddings. See :obj:`pytorch_widedeep.models.tab_transformer.SharedEmbeddings`
    frac_shared_embed: int, default = 8
        The fraction of embeddings that will be shared by all the different categories for
        one particular column.
    input_dim: int, default = 32
        The so-called *dimension of the model*. Is the number of embeddings used to encode
        the categorical columns
    n_heads: int, default = 8
        Number of attention heads per Transformer block
    n_blocks: int, default = 6
        Number of Transformer blocks
    dropout: float, default = 0.1
        Dropout that will be applied internally to the
        ``TransformerEncoder`` (see
        :obj:`pytorch_widedeep.model.tab_transformer.TransformerEncoder`) and the
        output MLP
    keep_attn_weights: bool, default = False
        If set to ``True`` the model will store the attention weights in the ``attention_weights``
        attribute.
    ff_hidden_dim: int, default = 128
        Hidden dimension of the ``FeedForward`` Layer. See
        :obj:`pytorch_widedeep.model.tab_transformer.FeedForward`.
    transformer_activation: str, default = "gelu"
        Transformer Encoder activation function
    with_special_token: bool, default = False,
        Boolean indicating if the special token ``[CLS]`` was used during the
        data pre-processing
    embed_continuous: bool, default = False,
        Boolean indicating if the continuous features will be "embedded"
        (i.e. each passed through a 1 layer MLP)
    cont_norm_layer: str, default =  "layernorm",
        Type of normalization layer applied to the continuous features if they
        are not embedded. Options are: 'layernorm' or 'batchnorm'.
    mlp_hidden_dims: List, Optional, default = None
        MLP hidden dimensions. If not provided it will default to ``[4*l,
        2*l]`` where ``l`` is the mlp input dimension
    mlp_activation: str, default = "gelu"
        MLP activation function
    mlp_batchnorm: bool, default = False
        Boolean indicating whether or not to apply batch normalization to the
        dense layers
    mlp_batchnorm_last: bool, default = False
        Boolean indicating whether or not to apply batch normalization to the
        last of the dense layers
    mlp_linear_first: bool, default = False
        Boolean indicating whether the order of the operations in the dense
        layer. If ``True: [LIN -> ACT -> BN -> DP]``. If ``False: [BN -> DP ->
        LIN -> ACT]``

    Attributes
    ----------
    cat_embed_layers: ``nn.ModuleDict``
        Dict with the embeddings per column
    cont_embed_layers: ``nn.ModuleDict``
        Dict with the embeddings per column if ``embed_continuous=True``
    cont_norm_layer: NormLayers
        Continuous normalization layer if ``continuous_cols`` is not None
    transformer_blks: ``nn.Sequential``
        Sequence of Transformer blocks
    attention_weights: List
        List with the attention weights per block
    transformer_mlp: ``nn.Module``
        MLP component in the model
    output_dim: int
        The output dimension of the model. This is a required attribute
        neccesary to build the WideDeep class

    Example
    --------
    >>> import torch
    >>> from pytorch_widedeep.models import TabTransformer
    >>> X_tab = torch.cat((torch.empty(5, 4).random_(4), torch.rand(5, 1)), axis=1)
    >>> colnames = ['a', 'b', 'c', 'd', 'e']
    >>> embed_input = [(u,i) for u,i in zip(colnames[:4], [4]*4)]
    >>> continuous_cols = ['e']
    >>> column_idx = {k:v for v,k in enumerate(colnames)}
    >>> model = TabTransformer(column_idx=column_idx, embed_input=embed_input, continuous_cols=continuous_cols)
    >>> out = model(X_tab)
    """

    def __init__(
        self,
        column_idx: Dict[str, int],
        embed_input: List[Tuple[str, int]],
        continuous_cols: Optional[List[str]] = None,
        embed_dropout: float = 0.1,
        full_embed_dropout: bool = False,
        shared_embed: bool = False,
        add_shared_embed: bool = False,
        frac_shared_embed: int = 8,
        input_dim: int = 32,
        n_heads: int = 8,
        n_blocks: int = 6,
        dropout: float = 0.1,
        keep_attn_weights: bool = False,
        ff_hidden_dim: int = 32 * 4,
        transformer_activation: str = "gelu",
        with_special_token: bool = False,
        embed_continuous: bool = False,
        cont_norm_layer: str = "layernorm",
        mlp_hidden_dims: Optional[List[int]] = None,
        mlp_activation: str = "relu",
        mlp_batchnorm: bool = False,
        mlp_batchnorm_last: bool = False,
        mlp_linear_first: bool = True,
    ):
        super(TabTransformer, self).__init__()

        self.column_idx = column_idx
        self.embed_input = embed_input
        self.continuous_cols = continuous_cols
        self.embed_dropout = embed_dropout
        self.full_embed_dropout = full_embed_dropout
        self.shared_embed = shared_embed
        self.add_shared_embed = add_shared_embed
        self.frac_shared_embed = frac_shared_embed
        self.input_dim = input_dim
        self.n_heads = n_heads
        self.n_blocks = n_blocks
        self.dropout = dropout
        self.keep_attn_weights = keep_attn_weights
        self.ff_hidden_dim = ff_hidden_dim
        self.transformer_activation = transformer_activation
        self.with_special_token = with_special_token
        self.embed_continuous = embed_continuous
        self.cont_norm_layer = cont_norm_layer
        self.mlp_hidden_dims = mlp_hidden_dims
        self.mlp_activation = mlp_activation
        self.mlp_batchnorm = mlp_batchnorm
        self.mlp_batchnorm_last = mlp_batchnorm_last
        self.mlp_linear_first = mlp_linear_first

        if "special_token" in self.column_idx and not self.with_special_token:
            raise ValueError(
                "The data was pre-processed using the 'CLS' special token,"
                " Please set 'with_special_token' to True"
            )

        self._set_categ_embeddings()

        self._set_cont_cols()

        self.transformer_blks = nn.Sequential()
        for i in range(n_blocks):
            self.transformer_blks.add_module(
                "block" + str(i),
                TransformerEncoder(
                    input_dim,
                    n_heads,
                    keep_attn_weights,
                    ff_hidden_dim,
                    dropout,
                    transformer_activation,
                ),
            )
        if keep_attn_weights:
            self.attention_weights: List[Any] = [None] * n_blocks

        if not mlp_hidden_dims:
            mlp_hidden_dims = self._set_mlp_hidden_dims()
        self.transformer_mlp = MLP(
            mlp_hidden_dims,
            mlp_activation,
            dropout,
            mlp_batchnorm,
            mlp_batchnorm_last,
            mlp_linear_first,
        )

        # the output_dim attribute will be used as input_dim when "merging" the models
        self.output_dim = mlp_hidden_dims[-1]

    def forward(self, X: Tensor) -> Tensor:

        cat_embed = [
            self.cat_embed_layers["emb_layer_" + col](
                X[:, self.column_idx[col]].long()
            ).unsqueeze(1)
            for col, _ in self.embed_input
        ]
        x = torch.cat(cat_embed, 1)
        if not self.shared_embed and self.embedding_dropout is not None:
            x = self.embedding_dropout(x)

        if self.continuous_cols is not None and self.embed_continuous:
            cont_embed = [
                self.cont_embed_layers["emb_layer_" + col](
                    X[:, self.column_idx[col]].float().unsqueeze(1)
                ).unsqueeze(1)
                for col in self.continuous_cols
            ]
            x_cont = torch.cat(cont_embed, 1)
            x = torch.cat([x, x_cont], 1)

        for i, blk in enumerate(self.transformer_blks):
            x = blk(x)
            if self.keep_attn_weights:
                if hasattr(blk, "row_attn"):
                    self.attention_weights[i] = (
                        blk.self_attn.attn_weights,
                        blk.row_attn.attn_weights,
                    )
                else:
                    self.attention_weights[i] = blk.self_attn.attn_weights

        if self.with_special_token:
            x = x[:, 0, :]
        else:
            x = x.flatten(1)

        if self.continuous_cols is not None and not self.embed_continuous:
            cont_idx = [self.column_idx[col] for col in self.continuous_cols]
            x_cont = self.cont_norm((X[:, cont_idx].float()))
            x = torch.cat([x, x_cont], 1)

        return self.transformer_mlp(x)

    def _set_categ_embeddings(self):
        # Categorical: val + 1 because 0 is reserved for padding/unseen cateogories.
        if self.shared_embed:
            self.cat_embed_layers = nn.ModuleDict(
                {
                    "emb_layer_"
                    + col: SharedEmbeddings(
                        val + 1,
                        self.input_dim,
                        self.embed_dropout,
                        self.full_embed_dropout,
                        self.add_shared_embed,
                        self.frac_shared_embed,
                    )
                    for col, val in self.embed_input
                }
            )
        else:
            self.cat_embed_layers = nn.ModuleDict(
                {
                    "emb_layer_"
                    + col: nn.Embedding(val + 1, self.input_dim, padding_idx=0)
                    for col, val in self.embed_input
                }
            )
            if self.full_embed_dropout:
                self.embedding_dropout: Union[
                    FullEmbeddingDropout, nn.Dropout
                ] = FullEmbeddingDropout(self.embed_dropout)
            else:
                self.embedding_dropout = nn.Dropout(self.embed_dropout)

    def _set_cont_cols(self):
        if self.continuous_cols is not None:
            if self.cont_norm_layer == "layernorm":
                self.cont_norm: NormLayers = nn.LayerNorm(len(self.continuous_cols))
            elif self.cont_norm_layer == "batchnorm":
                self.cont_norm = nn.BatchNorm1d(len(self.continuous_cols))
            if self.embed_continuous:
                self.cont_embed_layers = nn.ModuleDict(
                    {
                        "emb_layer_"
                        + col: nn.Sequential(nn.Linear(1, self.input_dim), nn.ReLU())
                        for col in self.continuous_cols
                    }
                )

    def _set_mlp_hidden_dims(self) -> List[int]:
        if self.continuous_cols is not None:
            if self.with_special_token:
                if self.embed_continuous:
                    mlp_hidden_dims = [
                        self.input_dim,
                        self.input_dim * 4,
                        self.input_dim * 2,
                    ]
                else:
                    mlp_inp_l = self.input_dim + len(self.continuous_cols)
                    mlp_hidden_dims = [mlp_inp_l, mlp_inp_l * 4, mlp_inp_l * 2]
            elif self.embed_continuous:
                mlp_inp_l = (
                    len(self.embed_input) + len(self.continuous_cols)
                ) * self.input_dim
                mlp_hidden_dims = [mlp_inp_l, mlp_inp_l * 4, mlp_inp_l * 2]
            else:
                mlp_inp_l = len(self.embed_input) * self.input_dim + len(
                    self.continuous_cols
                )
                mlp_hidden_dims = [mlp_inp_l, mlp_inp_l * 4, mlp_inp_l * 2]
        else:
            mlp_inp_l = len(self.embed_input) * self.input_dim
            mlp_hidden_dims = [mlp_inp_l, mlp_inp_l * 4, mlp_inp_l * 2]
        return mlp_hidden_dims


class SAINT(TabTransformer):
    r"""Adaptation of SAINT model
    (https://arxiv.org/abs/2106.01342) model that can be used as the
    deeptabular component of a Wide & Deep model.

    Parameters for this model are identical to those of the ``TabTransformer``

    Parameters
    ----------
    column_idx: Dict
        Dict containing the index of the columns that will be passed through
        the DeepDense model. Required to slice the tensors. e.g. {'education':
        0, 'relationship': 1, 'workclass': 2, ...}
    embed_input: List
        List of Tuples with the column name and number of unique values
        e.g. [(education, 11), ...]
    continuous_cols: List, Optional, default = None
        List with the name of the numeric (aka continuous) columns
    embed_dropout: float, default = 0.1
        Dropout to be applied to the embeddings matrix
    full_embed_dropout: bool, default = False
        Boolean indicating if an entire embedding (i.e. the representation
        for one categorical column) will be dropped in the batch. See:
        :obj:`pytorch_widedeep.model.tab_transformer.FullEmbeddingDropout`.
        If ``full_embed_dropout = True``, ``embed_dropout`` is ignored.
    shared_embed: bool, default = False
        The idea behind ``shared_embed`` is described in the Appendix A in the paper:
        `'The goal of having column embedding is to enable the model to distinguish the
        classes in one column from those in the other columns'`. In other words, the idea
        is to let the model learn which column is embedding at the time.
    add_shared_embed: bool, default = False,
        The two embedding sharing strategies are: 1) add the shared embeddings to the column
        embeddings or 2) to replace the first ``frac_shared_embed`` with the shared
        embeddings. See :obj:`pytorch_widedeep.models.tab_transformer.SharedEmbeddings`
    frac_shared_embed: int, default = 8
        The fraction of embeddings that will be shared by all the different categories for
        one particular column.
    input_dim: int, default = 32
        The so-called *dimension of the model*. Is the number of embeddings used to encode
        the categorical columns
    n_heads: int, default = 8
        Number of attention heads per Transformer block
    n_blocks: int, default = 6
        Number of Transformer blocks
    dropout: float, default = 0.1
        Dropout that will be applied internally to the
        ``TransformerEncoder`` (see
        :obj:`pytorch_widedeep.model.tab_transformer.TransformerEncoder`) and the
        output MLP
    keep_attn_weights: bool, default = False
        If set to ``True`` the model will store the attention weights in the ``attention_weights``
        attribute.
    ff_hidden_dim: int, default = 128
        Hidden dimension of the ``FeedForward`` Layer. See
        :obj:`pytorch_widedeep.model.tab_transformer.FeedForward`.
    transformer_activation: str, default = "gelu"
        Transformer Encoder activation function
    with_special_token: bool, default = False,
        Boolean indicating if the special token ``[CLS]`` was used during the
        data pre-processing
    embed_continuous: bool, default = False,
        Boolean indicating if the continuous features will be "embedded"
        (i.e. each passed through a 1 layer MLP)
    cont_norm_layer: str, default =  "layernorm",
        Type of normalization layer applied to the continuous features if they
        are not embedded. Options are: 'layernorm' or 'batchnorm'.
    mlp_hidden_dims: List, Optional, default = None
        MLP hidden dimensions. If not provided it will default to ``[4*l,
        2*l]`` where ``l`` is the mlp input dimension
    mlp_activation: str, default = "gelu"
        MLP activation function
    mlp_batchnorm: bool, default = False
        Boolean indicating whether or not to apply batch normalization to the
        dense layers
    mlp_batchnorm_last: bool, default = False
        Boolean indicating whether or not to apply batch normalization to the
        last of the dense layers
    mlp_linear_first: bool, default = False
        Boolean indicating whether the order of the operations in the dense
        layer. If ``True: [LIN -> ACT -> BN -> DP]``. If ``False: [BN -> DP ->
        LIN -> ACT]``

    Attributes
    ----------
    cat_embed_layers: ``nn.ModuleDict``
        Dict with the embeddings per column
    cont_embed_layers: ``nn.ModuleDict``
        Dict with the embeddings per column if ``embed_continuous=True``
    cont_norm_layer: NormLayers
        Continuous normalization layer if ``continuous_cols`` is not None
    transformer_blks: ``nn.Sequential``
        Sequence of Transformer blocks
    attention_weights: List
        List with the attention weights per block
    transformer_mlp: ``nn.Module``
        MLP component in the model
    output_dim: int
        The output dimension of the model. This is a required attribute
        neccesary to build the WideDeep class

    Example
    --------
    >>> import torch
    >>> from pytorch_widedeep.models import SAINT
    >>> X_tab = torch.cat((torch.empty(5, 4).random_(4), torch.rand(5, 1)), axis=1)
    >>> colnames = ['a', 'b', 'c', 'd', 'e']
    >>> embed_input = [(u,i) for u,i in zip(colnames[:4], [4]*4)]
    >>> continuous_cols = ['e']
    >>> column_idx = {k:v for v,k in enumerate(colnames)}
    >>> model = SAINT(column_idx=column_idx, embed_input=embed_input, continuous_cols=continuous_cols)
    >>> out = model(X_tab)
    """

    def __init__(
        self,
        column_idx: Dict[str, int],
        embed_input: List[Tuple[str, int]],
        continuous_cols: Optional[List[str]] = None,
        embed_dropout: float = 0.1,
        full_embed_dropout: bool = False,
        shared_embed: bool = False,
        add_shared_embed: bool = False,
        frac_shared_embed: int = 8,
        input_dim: int = 32,
        n_heads: int = 8,
        n_blocks: int = 6,
        dropout: float = 0.1,
        keep_attn_weights: bool = False,
        ff_hidden_dim: int = 32 * 4,
        transformer_activation: str = "gelu",
        with_special_token: bool = False,
        embed_continuous: bool = False,
        cont_norm_layer: str = "layernorm",
        mlp_hidden_dims: Optional[List[int]] = None,
        mlp_activation: str = "relu",
        mlp_batchnorm: bool = False,
        mlp_batchnorm_last: bool = False,
        mlp_linear_first: bool = True,
    ):
        super().__init__(
            column_idx,
            embed_input,
            continuous_cols,
            embed_dropout,
            full_embed_dropout,
            shared_embed,
            add_shared_embed,
            frac_shared_embed,
            input_dim,
            n_heads,
            n_blocks,
            dropout,
            keep_attn_weights,
            ff_hidden_dim,
            transformer_activation,
            with_special_token,
            embed_continuous,
            cont_norm_layer,
            mlp_hidden_dims,
            mlp_activation,
            mlp_batchnorm,
            mlp_batchnorm_last,
            mlp_linear_first,
        )

        if embed_continuous:
            n_feats = len(embed_input) + len(continuous_cols)
        else:
            n_feats = len(embed_input)
        self.transformer_blks = nn.Sequential()
        for i in range(n_blocks):
            self.transformer_blks.add_module(
                "block" + str(i),
                SaintEncoder(
                    input_dim,
                    n_heads,
                    keep_attn_weights,
                    ff_hidden_dim,
                    dropout,
                    transformer_activation,
                    n_feats,
                ),
            )
