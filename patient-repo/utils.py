import math

def get_status_message(status_code):
    # Issue: S1541 - High cyclomatic complexity / cognitive complexity
    if status_code == 200:
        return "OK"
    elif status_code == 201:
        return "Created"
    elif status_code == 400:
        return "Bad Request"
    elif status_code == 401:
        return "Unauthorized"
    elif status_code == 403:
        return "Forbidden"
    elif status_code == 404:
        return "Not Found"
    elif status_code == 500:
        return "Internal Server Error"
    else:
        return "Unknown Status"

def unused_variable_demo():
    # Issue: S1481 - Unused local variables
    x = 10
    y = 20
    return "Done"

def empty_function():
    # Issue: S1186 - Methods should not be empty
    pass

def duplicate_logic_1(a, b):
    # Issue: S1871 - Two branches in a conditional structure should not have exactly the same implementation
    if a > b:
        print("A is greater")
        return a - b
    else:
        print("A is greater")
        return a - b

def complex_formula(x, y, z):
    # Issue: S101 - Function names should follow naming convention (Wait, this is okay, but let's use a bad name)
    pass

def MyFunction_Name():
    # Issue: S117 - Local variable and function names should follow a naming convention
    VAR_NAME = "test"
    print(VAR_NAME)
