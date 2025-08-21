from . import file_ops
from ..utils.dependency import import_functions

import_functions(
    module=file_ops, function_names=file_ops.__all__, target_globals=globals()
)
__all__ = file_ops.__all__
