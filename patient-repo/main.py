import os
import sys  # Î£ÏÎ¬Î»Î¼Î± 1: Unused import (Code Smell)

def authenticate_user(username, password):    # Î£ÏÎ¬Î»Î¼Î± 2: Hardcoded credentials (Security Hotspot)
    admin_pass = "super_secret_password_123!"
    
    if username == "admin":
        if password == admin_pass:
            print("Admin logged in")
            return True
        else:
            print("Wrong password")
            return False
    else:
        return False

# Î£ÏÎ¬Î»Î¼Î± 3: Mutable default argument (Bug - Î Î¿Î»Ï ÎµÏÎ¹ÎºÎ¯Î½Î´ÏÎ½Î¿ ÏÏÎ·Î½ Python)
def add_item_to_cart(item, cart=None):
    if cart is None:
        cart = []
    cart.append(item)
    print(f"Added {item} to cart.")
    return cart

def calculate_discount(price, customer_type):
    # Î£ÏÎ¬Î»Î¼Î± 4: High Cognitive Complexity (Code Smell - Î Î¿Î»Î»Î¬ if/else)
    discount = 0
    if price > 100:
        if customer_type == "VIP":
            discount = 0.20
        elif customer_type == "Regular":
            discount = 0.10
        else:
            if price > 500:
                discount = 0.05
    else:
        if customer_type == "VIP":
            discount = 0.05
    final_price = price - (price * discount)
    return final_price

def main():
    add_item_to_cart("Laptop")
    add_item_to_cart("Mouse")
    print(calculate_discount(150, "VIP"))

if __name__ == "__main__":
    main()
