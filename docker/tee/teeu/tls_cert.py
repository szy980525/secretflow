import datetime
import socket


def generate_self_signed_tls_certs(cert_path: str, key_path: str):
    """Create self-signed key/cert pair for testing.
    This method requires the library ``cryptography`` be installed.
    """
    try:
        from cryptography import x509
        from cryptography.hazmat.backends import default_backend
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
    except ImportError:
        raise ImportError(
            "Using `Security.temporary` requires `cryptography`, please "
            "install it using either pip or conda"
        )
    key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    key_contents = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()

    ray_interal = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ray-internal")])
    # This is the same logic used by the GCS server to acquire a
    # private/interal IP address to listen on. If we just use localhost +
    # 127.0.0.1 then we won't be able to connect to the GCS and will get
    # an error like "No match found for server name: 192.168.X.Y"
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    private_ip_address = s.getsockname()[0]
    s.close()
    altnames = x509.SubjectAlternativeName(
        [
            # x509.DNSName(
            #     socket.gethostbyname(socket.gethostname())
            # ),  # Probably 127.0.0.1
            x509.DNSName("127.0.0.1"),
            x509.DNSName(private_ip_address),  # 192.168.*.*
            x509.DNSName("localhost"),
        ]
    )
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(ray_interal)
        .issuer_name(ray_interal)
        .add_extension(altnames, critical=False)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256(), default_backend())
    )

    cert_contents = cert.public_bytes(serialization.Encoding.PEM).decode()
    with open(cert_path, "w") as fh:
        fh.write(cert_contents)
    with open(key_path, "w") as fh:
        fh.write(key_contents)

    return cert_contents, key_contents
