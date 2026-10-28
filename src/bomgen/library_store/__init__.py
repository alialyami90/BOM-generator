"""Device-library update packages (`.bomlib`) and the per-user installed-library store.

See ADR 0008 and plan milestone M8. Other code uses `validate_library`,
`import_library`, `preview_library_import` (the import dry-run) and
`load_device_records` (the device-database records of an installed version) and
`save_local_version` (an edited library saved as `<base>+local.<n>`, ADR 0018);
refusals are `LibraryPackageError` with a `RefusalKind`.
"""

from bomgen.library_store.device_db import DeviceRecord, load_device_records
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import LocalSave, save_local_version
from bomgen.library_store.preview import LibraryImportPreview, preview_library_import
from bomgen.library_store.service import import_library, validate_library

__all__ = [
    "DeviceRecord",
    "LibraryImportPreview",
    "LibraryPackageError",
    "LocalSave",
    "RefusalKind",
    "import_library",
    "load_device_records",
    "preview_library_import",
    "save_local_version",
    "validate_library",
]
