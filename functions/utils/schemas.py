from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Literal
from datetime import datetime
from firebase_admin.firestore import GeoPoint

# Product Schema
class ProductSchema(BaseModel):
    name: str = Field(..., title="Name of the Product", max_length=100)
    description: str = Field(..., max_length=500, title="Description of the Product")
    price: float = Field(..., ge=0, description="Price of the Product, must be non-negative")
    quantity: int = Field(..., ge=0, title="Quantity of the Product", description="Stock quantity, must be non-negative")
    location: Optional[Dict[str, float]] = Field(
        None, description="Geolocation of the product as {'latitude': float, 'longitude': float}"
    )

    @validator("location")
    def validate_location(cls, loc):
        if loc and ("latitude" not in loc or "longitude" not in loc):
            raise ValueError("Location must contain 'latitude' and 'longitude'")
        return loc

# User Schema
class UserSchema(BaseModel):
    phone_number: str = Field(..., regex=r'^\+?[1-9]\d{1,14}$', title="User's Phone Number")
    password: Optional[str] = Field(None, title="User's Password (for non-OTP cases)")
    email: Optional[str] = Field(None, regex=r'^[\w\.-]+@[\w\.-]+\.\w+$', title="User's Email Address")
    name: Optional[str] = Field(None, max_length=100)
    type: str = Field(..., regex=r'^(researcher|ngo|farmer|buyer)$', title="User Type")
    description: Optional[str] = Field(None, max_length=500)
    location: Optional[Dict[str, float]] = Field(
        None, description="Geolocation as {'latitude': float, 'longitude': float}"
    )
    focus_area: Optional[str] = Field(None, title="Focus area for researcher/NGO users", max_length=200)

    @validator("location")
    def validate_location(cls, loc):
        if loc and ("latitude" not in loc or "longitude" not in loc):
            raise ValueError("Location must contain 'latitude' and 'longitude'")
        return loc

    @validator("password", always=True)
    def validate_password_or_otp(cls, pwd, values):
        if not pwd and not values.get("phone_number"):
            raise ValueError("Password or valid OTP must be provided.")
        return pwd

# Order Schema
class OrderSchema(BaseModel):
    product_id: str = Field(..., title="Product ID", description="ID of the product being ordered")
    user_id: str = Field(..., title="User ID", description="ID of the user placing the order")
    quantity: int = Field(..., ge=1, title="Quantity", description="Number of items being ordered")
    price_per_unit: float = Field(..., ge=0, title="Price per Unit", description="Price of a single unit")
    total_amount: float = Field(..., ge=0, title="Total Amount", description="Total price for the order")
    order_date: datetime = Field(default_factory=datetime.utcnow, title="Order Date", description="Date and time of order creation")
    order_status: Literal['created', 'packed', 'shipped', 'delivered'] = Field(
        ..., title="Order Status", description="Status of the order"
    )

    @validator("total_amount", always=True)
    def calculate_total_amount(cls, total_amount, values):
        quantity = values.get("quantity", 0)
        price_per_unit = values.get("price_per_unit", 0)
        return quantity * price_per_unit