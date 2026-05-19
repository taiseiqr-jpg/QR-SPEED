from django.db import models
from ninja import Schema
import uuid



class Worker(models.Model):
    ROLE_CHOICES = [
        ("admin", "Admin"),
        ("user", "User"),
    ]
    employee_id = models.CharField(max_length=50, primary_key= True)
    first_name = models.CharField(max_length=25)
    last_name = models.CharField(max_length=20)
    username = models.CharField(max_length=50)

    role = models.CharField(max_length=6, choices=ROLE_CHOICES, default="user")

class Customer(models.Model):
    customer_name = models.CharField(max_length=20)

    class Meta:
        indexes = [
            models.Index(fields=["customer_name"]),
        ]

    def __str__(self):
        return self.customer_name


class Item(models.Model):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="items",
        null=True,  # you can remove null=True if all items must have a customer
        blank=True
    )
    item = models.CharField(max_length=80)

    class Meta:
        unique_together = ("customer", "item")
        indexes = [
            models.Index(fields=["item"]),
            models.Index(fields=["customer", "item"]),
        ]

    def __str__(self):
        return self.item


class Partname(models.Model):
    item = models.ForeignKey(
        Item,
        on_delete=models.CASCADE,
        related_name="partnames"
    )
    part_name = models.CharField(max_length=100)
    maker = models.CharField(max_length=20)

    class Meta:
        unique_together = ("item", "part_name")  # fixed: ensure part_name is unique per item
        indexes = [
            models.Index(fields=["part_name"]),
            models.Index(fields=["maker"]),
            models.Index(fields=["item", "part_name"]),
        ]

    def __str__(self):
        return f"{self.part_name} ({self.maker})"
    


class Product(models.Model):
    item_code = models.CharField (max_length=100)
    part_no = models.CharField(max_length=100)
    process = models.JSONField(default= dict)
    customer = models.CharField(max_length=40)
    product_family = models.CharField(max_length=75)


class WorkerOutput(models.Model):
    lot_no = models.IntegerField()

    STATUS_CHOICE = [("ongoing","Ongoing"),("onhold","On Hold"),("finished","Finished")]

    current_status = models.CharField(max_length=20, choices= STATUS_CHOICE)
    output_data = models.JSONField()
    current_process_index = models.IntegerField(default=0)

class EmployeeCSV(models.Model):
    file = models.FileField()
    

class QRCode(models.Model):
    """Model for storing QR code data and generated QR codes"""
    
    # Status choices
    class Status(models.TextChoices):
        GOOD = 'GOOD', 'Good'
        NO_GOOD = 'NO_GOOD', 'No Good'
    
    # Store the item and part information from masterlist
    item_name = models.CharField(max_length=255)
    part_name = models.CharField(max_length=255)  # Specific part selected
    part_maker = models.CharField(max_length=255)
    
    # QR data fields
    lot_no = models.CharField(max_length=100)
    
    # Status (will be blank/null if not scanned yet)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        null=True,
        blank=True,
        db_index=True
    )
    
    # Verification timestamp
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    qr_uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=255, blank=True, null=True)
    
    # QR code image
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['qr_uuid']),
            models.Index(fields=['lot_no']),
            models.Index(fields=['item_name', 'part_name']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"QR-{self.qr_uuid}: {self.item_name} - {self.part_name} (Lot: {self.lot_no})"
    
    def generate_qr_data(self):
        """
        Generate the data to be encoded in QR.
        Only contains: item, partname, lot no, and status (blank if not scanned)
        """
        data = {
            "item": self.item_name,
            "part": self.part_name,
            "maker": self.part_maker,
            "lot": self.lot_no,
        }
        
        # Only add status if it has been set (scanned)
        if self.status:
            data["status"] = self.status
        
        return {
            "qr_uuid": str(self.qr_uuid),
            "item": self.item_name,
            "part": {
                "name": self.part_name,
                "maker": self.part_maker
            },
            "lot_no": self.lot_no,
            "status": self.status
        }


class VerificationLog(models.Model):
    """Model for storing QR verification logs"""

    class Result(models.TextChoices):
        GOOD = 'GOOD', 'Good'
        NO_GOOD = 'NO_GOOD', 'No Good'

    qr_uuid = models.UUIDField()
    qr_item = models.CharField(max_length=255)
    part_name = models.CharField(max_length=255, blank=True, null=True)
    part_maker = models.CharField(max_length=255, blank=True, null=True)
    lot_no = models.CharField(max_length=100, blank=True, null=True)
    user_item = models.CharField(max_length=255)
    user_part = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=Result.choices)
    result = models.CharField(max_length=20, choices=Result.choices)
    backend_updated = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)
    verified_by = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['qr_uuid']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['status']),
            models.Index(fields=['result']),
        ]

    def __str__(self):
        return f"VerificationLog-{self.id}: {self.qr_uuid} - {self.result}"



'''
    @api.post("/item/{itemcode}/process/", tags=['UPDATE PROCESS'])
def update_process(request, data: ProductSchema, itemcode: str):
    # Fetch the product directly
    product = Product.objects.get(item_code=itemcode)
    
    # Use the existing process directly
    process_existing = product.process  # Access existing process directly
    process_new_entry = data.process  # Assuming this is the new data to append

    # To not leave empty string being stored in process
    if not process_new_entry or all(not process for process in process_new_entry):
        return {"message": "Process list cannot be empty."}

    # Append new process data without altering existing data
    product.process.extend(process_new_entry)  # Use extend to add new entries
    error_messages = []  # Use for storing wrong process code length
    for index, process in enumerate(process_new_entry):
        for key in process.keys():
            if len(key) != 4:  # Checking length of process code is equal to 4
                error_messages.append(f"Key '{key}' in entry {index} is not 4 characters long.")
    
    if error_messages:
        return {"messages": error_messages}
    
    product.save()
    final_process = sorted(
        product.process,  # Sort the updated process list
        key=lambda x: (list(x.keys())[0][0], int(list(x.keys())[0][1:]))
    )
    
    return {
        "message": "Processes updated successfully!",
        "item_code": product.item_code,
        "part_no": product.part_no,
        "process": final_process,
        "customer": product.customer,
        "product_family": product.product_family
    }'''
