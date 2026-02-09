import csv
from io import StringIO
from django.http import HttpResponse
from django.utils import timezone
from .models import EFTBatch

class EFTGenerator:
    """Generates RBM-compliant EFT files for Python 3.14"""
    
    @staticmethod
    def validate_batch(batch: EFTBatch) -> bool:
        """Validate batch before generation"""
        if batch.status != 'APPROVED':
            raise ValueError("Only approved batches can be exported")
        
        transactions = batch.transactions.all()
        
        if not transactions.exists():
            raise ValueError("Batch has no transactions")
        
        # Calculate totals
        total_amount = sum(t.amount for t in transactions)
        record_count = transactions.count()
        
        # Validate totals
        if abs(total_amount - batch.total_amount) > 0.01:
            raise ValueError(f"Transaction total ({total_amount}) doesn't match batch total ({batch.total_amount})")
        
        if record_count != batch.record_count:
            raise ValueError(f"Transaction count ({record_count}) doesn't match batch record count ({batch.record_count})")
        
        # Validate required fields
        for trans in transactions:
            required_fields = [
                (trans.debit_account, "Debit account"),
                (trans.supplier, "Supplier"),
                (trans.supplier.bank, "Supplier bank"),
                (trans.scheme, "Scheme"),
                (trans.zone, "Zone"),
            ]
            
            for field, name in required_fields:
                if not field:
                    raise ValueError(f"{name} is required for transaction {trans.sequence_number}")
        
        return True
    
    @staticmethod
    def format_amount(amount) -> str:
        """Format amount to 2 decimal places"""
        return f"{float(amount):.2f}"
    
    @staticmethod
    def generate_eft_file(batch: EFTBatch) -> str:
        """Generate EFT file content for approved batch"""
        # Validate batch
        EFTGenerator.validate_batch(batch)
        
        transactions = batch.transactions.all().order_by('sequence_number')
        
        # Calculate totals
        total_amount = sum(t.amount for t in transactions)
        record_count = transactions.count()
        
        output = StringIO()
        writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_NONE, escapechar='\\')
        
        # Write header record (Type 0)
        writer.writerow([
            '0',
            batch.batch_name[:50],
            batch.currency,
            EFTGenerator.format_amount(total_amount),
            f"{record_count:04d}"
        ])
        
        # Write body records (Type 1)
        for trans in transactions:
            writer.writerow([
                '1',
                trans.sequence_number.zfill(4),
                batch.currency,
                trans.debit_account.account_number,
                trans.zone.zone_code,
                EFTGenerator.format_amount(trans.amount),
                trans.supplier.supplier_name[:55],
                trans.scheme.scheme_code,
                '', '',  # Empty fields
                trans.supplier.credit_reference or '',
                trans.supplier.bank.swift_code,
                trans.supplier.account_number,
                '', '',  # Empty fields
                trans.reference_number or '',
                trans.narration[:200] if trans.narration else ''
            ])
        
        content = output.getvalue()
        output.close()
        
        # Save to batch
        batch.generated_file = content
        batch.generated_at = timezone.now()
        batch.save(update_fields=['generated_file', 'generated_at'])
        
        return content
    
    @staticmethod
    def export_to_txt(content: str, filename: str) -> HttpResponse:
        """Export content to TXT file"""
        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}.txt"'
        return response
    
    @staticmethod
    def export_to_csv(content: str, filename: str) -> HttpResponse:
        """Export content to CSV file"""
        response = HttpResponse(content, content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    @staticmethod
    def validate_eft_structure(content: str) -> tuple[bool, str]:
        """Validate EFT file structure"""
        lines = content.strip().split('\n')
        
        if not lines:
            return False, "Empty file"
        
        # Check header
        header_parts = lines[0].split(';')
        if len(header_parts) != 5:
            return False, "Invalid header format"
        
        if header_parts[0] != '0':
            return False, "Header must start with 0"
        
        try:
            record_count = int(header_parts[4])
        except ValueError:
            return False, "Invalid record count in header"
        
        # Check body records
        if len(lines) - 1 != record_count:
            return False, f"Record count mismatch: header says {record_count}, file has {len(lines)-1}"
        
        total_amount = 0.0
        for i, line in enumerate(lines[1:], 1):
            parts = line.split(';')
            if len(parts) != 17:
                return False, f"Line {i}: Invalid number of fields ({len(parts)} instead of 17)"
            
            if parts[0] != '1':
                return False, f"Line {i}: Body record must start with 1"
            
            try:
                amount = float(parts[5])
                total_amount += amount
            except ValueError:
                return False, f"Line {i}: Invalid amount format"
        
        # Validate total amount
        try:
            header_amount = float(header_parts[3])
            if abs(total_amount - header_amount) > 0.01:
                return False, f"Total amount mismatch: header says {header_amount}, sum is {total_amount}"
        except ValueError:
            return False, "Invalid total amount in header"
        
        return True, "EFT file structure is valid"