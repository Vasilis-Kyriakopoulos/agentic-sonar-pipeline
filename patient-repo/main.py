import os
import sys

# Issue: S1135 - TODO tags should be handled
# TODO: Implement a real database connection

def add_numbers(a, b, c, d, e, f):
    # Issue: S107 - Too many parameters
    return a + b + c + d + e + f

def process_data(data=[]):
    # Issue: S5717 - Mutable default argument
    data.append("processed")
    return data

def check_access(user_role):
    # Issue: S3776 - High Cognitive Complexity
    if user_role == "admin":
        print("Access granted")
        return True
    else:
        if user_role == "manager":
            print("Partial access")
            return True
        else:
            if user_role == "guest":
                print("Limited access")
                return True
            else:
                print("Access denied")
                return False

def calculate_area(radius):
    # Issue: S905 - Unnecessary parentheses
    area = (3.14159 * (radius ** 2))
    return (area)

def main():
    # Issue: S1192 - String literals should not be duplicated
    print("Welcome to the system")
    print("Welcome to the system")
    
    # Issue: S125 - Commented out code
    # result = add_numbers(1, 2, 3, 4, 5, 6)
    # print(result)
    
    items = process_data()
    print(items)
    
    check_access("guest")

if __name__ == "__main__":
    main()
