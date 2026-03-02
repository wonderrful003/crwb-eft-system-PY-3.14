"""
EFT File Generator — RBM-compliant format.

HEADER (5 fields, semicolon-delimited):
  0  Header Line Identifier   = "0"  (constant)
  1  File Reference           = max 16 chars
  2  Currency Code            = 3 chars  e.g. MWK
  3  File Total               = number with 2 decimal places
  4  Total Count              = plain integer

BODY (16 fields per transaction, semicolon-delimited):
  0  Line Items Identifier    = "1"  (constant)
  1  Trans Serial             = plain integer (line-item count)
  2  Currency Code            = 3 chars
  3  Debit Account Number     = max 20 chars
  4  Debit Account Name       = max 55 chars
  5  Payment Amount           = number with 2 decimal places
  6  Payee Details            = max 55 chars  (Beneficiary account name)
  7  Vendor Code              = max 7 chars   (UDF1 at UBS)
  8  Employee Number          = max 6 chars   (UDF2 at UBS)  — optional
  9  National ID              = max 8 chars   (UDF3 at UBS)  — optional
  10 Invoice Number           = max 16 chars  (Payee's Reference Number)
  11 Payee BIC                = max 11 chars  (Beneficiary Bank BIC)
  12 Credit Account Number    = max 20 chars
  13 Cost Center              = max 50 chars  (Originating Cost/Funds Centre) — optional
  14 Source reference         = max 18 chars  (IFMIS reference)
  15 Description              = max 200 chars
"""
import csv
from io import StringIO
from django.http import HttpResponse
from django.utils import timezone
from .models import EFTBatch


class EFTGenerator:

    @staticmethod
    def validate_batch(batch: EFTBatch) -> bool:
        if batch.status != 'APPROVED':
            raise ValueError("Only approved batches can be exported")

        transactions = batch.transactions.all()
        if not transactions.exists():
            raise ValueError("Batch has no transactions")

        total_amount = sum(t.amount for t in transactions)
        record_count = transactions.count()

        if abs(total_amount - batch.total_amount) > 0.01:
            raise ValueError(
                f"Transaction total ({total_amount}) doesn't match batch total ({batch.total_amount})"
            )
        if record_count != batch.record_count:
            raise ValueError(
                f"Transaction count ({record_count}) doesn't match batch record count ({batch.record_count})"
            )

        for trans in transactions:
            if not trans.supplier:
                raise ValueError(f"Supplier is required for transaction {trans.sequence_number}")
            if not trans.supplier.supplier_code:
                raise ValueError(f"Vendor Code (supplier_code) required for transaction {trans.sequence_number}")
            if not trans.supplier.account_name:
                raise ValueError(f"Payee Details (account_name) required for transaction {trans.sequence_number}")
            if not trans.supplier.bank or not trans.supplier.bank.swift_code:
                raise ValueError(f"Bank SWIFT code required for transaction {trans.sequence_number}")
            if not trans.supplier.account_number:
                raise ValueError(f"Credit Account Number required for transaction {trans.sequence_number}")
            if not trans.debit_account:
                raise ValueError(f"Debit account required for transaction {trans.sequence_number}")
            if not trans.reference_number:
                raise ValueError(f"Invoice Number required for transaction {trans.sequence_number}")
            if not trans.source_reference:
                raise ValueError(f"Source Reference required for transaction {trans.sequence_number}")
            if not trans.narration:
                raise ValueError(f"Description required for transaction {trans.sequence_number}")

        return True

    @staticmethod
    def format_amount(amount) -> str:
        return f"{float(amount):.2f}"

    @staticmethod
    def generate_eft_file(batch: EFTBatch) -> str:
        EFTGenerator.validate_batch(batch)

        transactions = batch.transactions.all().order_by('sequence_number')
        total_amount = sum(t.amount for t in transactions)
        record_count = transactions.count()

        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_NONE, escapechar='\\')

        # ── HEADER RECORD (5 fields) ──────────────────────────────────────────
        writer.writerow([
            '0',                                                   # Field 0: Header Line Identifier
            (batch.file_reference or batch.batch_reference)[:16], # Field 1: File Reference (max 16)
            batch.currency,                                        # Field 2: Currency Code
            EFTGenerator.format_amount(total_amount),              # Field 3: File Total
            str(record_count),                                     # Field 4: Total Count
        ])

        # ── BODY RECORDS (16 fields each) ─────────────────────────────────────
        for trans in transactions:
            cost_center = trans.cost_center
            if not cost_center and trans.scheme:
                cost_center = trans.scheme.default_cost_center

            writer.writerow([
                '1',                                               # Field  0: Line Items Identifier
                str(int(trans.sequence_number)).zfill(4),          # Field  1: Trans Serial (padded to 4 digits)                   # Field  1: Trans Serial
                batch.currency,                                    # Field  2: Currency Code
                trans.debit_account.account_number[:20],           # Field  3: Debit Account Number
                trans.debit_account.account_name[:55],             # Field  4: Debit Account Name
                EFTGenerator.format_amount(trans.amount),          # Field  5: Payment Amount
                trans.supplier.account_name[:55],                  # Field  6: Payee Details (beneficiary name)
                trans.supplier.supplier_code[:7],                  # Field  7: Vendor Code (UDF1)
                (trans.employee_number or '')[:6],                 # Field  8: Employee Number (UDF2)
                (trans.national_id or '')[:8],                     # Field  9: National ID (UDF3)
                trans.reference_number[:16],                       # Field 10: Invoice Number / Payee's Reference
                trans.supplier.bank.swift_code[:11],               # Field 11: Payee BIC
                trans.supplier.account_number[:20],                # Field 12: Credit Account Number
                (cost_center or '')[:50],                          # Field 13: Cost Centre
                trans.source_reference[:18],                       # Field 14: Source reference (IFMIS)
                trans.narration[:200],                             # Field 15: Description
            ])

        content = output.getvalue()
        output.close()

        batch.generated_file = content
        batch.generated_at = timezone.now()
        batch.save(update_fields=['generated_file', 'generated_at'])

        return content

    @staticmethod
    def export_to_txt(content: str, filename: str) -> HttpResponse:
        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}.txt"'
        return response

    @staticmethod
    def export_to_csv(content: str, filename: str) -> HttpResponse:
        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    @staticmethod
    def validate_eft_structure(content: str) -> tuple[bool, str]:
        lines = content.strip().split('\n')
        if not lines:
            return False, "Empty file"

        # ── Validate header ───────────────────────────────────────────────────
        header_parts = lines[0].split(';')
        if len(header_parts) != 5:
            return False, f"Invalid header: expected 5 fields, got {len(header_parts)}"
        if header_parts[0] != '0':
            return False, "Header must start with '0'"
        if len(header_parts[1]) > 16:
            return False, f"File Reference exceeds 16 characters ({len(header_parts[1])})"

        try:
            record_count = int(header_parts[4])
        except ValueError:
            return False, "Invalid record count in header"

        if len(lines) - 1 != record_count:
            return False, f"Record count mismatch: header says {record_count}, file has {len(lines) - 1}"

        # ── Validate body records ─────────────────────────────────────────────
        total_amount = 0.0
        for i, line in enumerate(lines[1:], 1):
            parts = line.split(';')
            if len(parts) != 16:
                return False, f"Line {i}: expected 16 fields, got {len(parts)}"
            if parts[0] != '1':
                return False, f"Line {i}: body record must start with '1'"

            # Mandatory field checks (by position)
            checks = {
                3:  "Debit Account Number",
                4:  "Debit Account Name",
                6:  "Payee Details",
                7:  "Vendor Code",
                10: "Invoice Number",
                11: "Payee BIC",
                12: "Credit Account Number",
                14: "Source reference",
                15: "Description",
            }
            for pos, label in checks.items():
                if not parts[pos].strip():
                    return False, f"Line {i}: {label} (field {pos}) is required"

            try:
                amount = float(parts[5])
                total_amount += amount
            except ValueError:
                return False, f"Line {i}: invalid amount format in field 5"

        try:
            header_amount = float(header_parts[3])
            if abs(total_amount - header_amount) > 0.01:
                return False, f"Amount mismatch: header total {header_amount}, sum of lines {total_amount:.2f}"
        except ValueError:
            return False, "Invalid total amount in header"

        return True, "EFT file structure is valid"