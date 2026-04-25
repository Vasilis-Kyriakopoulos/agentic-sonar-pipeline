import hashlib
import pickle
import subprocess

def login(username, password):
    # Issue: S2068 - Hardcoded credentials
    ADMIN_PASSWORD = "Password123!"
    if username == "admin" and password == ADMIN_PASSWORD:
        return True
    return False

def hash_password(password):
    # Issue: S2070 - SHA-1 and Message-Digest hash algorithms should not be used in secure contexts
    m = hashlib.sha1()
    m.update(password.encode('utf-8'))
    return m.hexdigest()

def execute_command(cmd):
    # Issue: S2076 - OS commands should not be vulnerable to command injection
    subprocess.call(cmd, shell=True)

def load_data(serialized_data):
    # Issue: S5046 - Deserializing data with "pickle" is unsafe
    return pickle.loads(serialized_data)

def insecure_temp_file():
    # Issue: S5443 - Using "tempfile.mktemp()" is insecure
    import tempfile
    filename = tempfile.mktemp()
    with open(filename, "w") as f:
        f.write("sensitive data")
