"""Device-library update packages (`.bomlib`) and the per-user installed-library store.

See ADR 0008 and plan milestone M8. Other code uses `validate_library`,
`import_library`, `preview_library_import` (the import dry-run),
`load_device_records` (the device-database records of an installed version) and
`save_edits` and `save_local_version` (an edited library saved as `<base>+local.<n>`,
ADR 0018; `record_edits` edit the device-database records, checked per field with
`check_record_field` and previewed with `apply_record_edits`), and `preview_csv_import` /
`import_csv` / `export_csv` (the CSV tables);
refusals are `LibraryPackageError` with a `RefusalKind`.
"""

from bomgen.library_store.alternatives import AlternativeRow, compare_alternatives
from bomgen.library_store.csv_export import export_csv
from bomgen.library_store.csv_import import CsvPreview, import_csv, preview_csv_import
from bomgen.library_store.device_db import DeviceRecord, load_device_records
from bomgen.library_store.errors import LibraryPackageError, RefusalKind
from bomgen.library_store.local import LocalSave, save_edits, save_local_version
from bomgen.library_store.preview import LibraryImportPreview, preview_library_import
from bomgen.library_store.records import RecordEditResult, apply_record_edits, check_record_field
from bomgen.library_store.service import import_library, validate_library

__all__ = [
    "AlternativeRow",
    "CsvPreview",
    "DeviceRecord",
    "LibraryImportPreview",
    "LibraryPackageError",
    "LocalSave",
    "RecordEditResult",
    "RefusalKind",
    "apply_record_edits",
    "check_record_field",
    "compare_alternatives",
    "export_csv",
    "import_csv",
    "import_library",
    "load_device_records",
    "preview_csv_import",
    "preview_library_import",
    "save_edits",
    "save_local_version",
    "validate_library",
]
