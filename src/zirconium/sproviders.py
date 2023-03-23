import logging
from urllib.parse import urlparse
try:
    from azure.identity import DefaultAzureCredential
    from azure.keyvault.secrets import SecretClient
    from azure.core.exceptions import HttpResponseError
    AZURE_ENABLED = True
except ImportError:
    AZURE_ENABLED = False


def azure_key_vault(secret_path):
    # Expects https://KEY_VAULT.vault.azure.net/SECRET_NAME
    if not AZURE_ENABLED:
        logging.getLogger("zirconium").warning("Azure KeyVault requested but client libraries not installed")
        return None
    parts = urlparse(secret_path)
    if not parts.hostname.endswith(".vault.azure.net"):
        logging.getLogger("zirconium").warning("Azure KeyVault requires .vault.azure.net paths")
        return None
    key_vault = f"https://{parts.hostname}"
    secret_name = parts.path
    if secret_name.startswith("/"):
        secret_name = secret_name[1:]
    credentials = DefaultAzureCredential()
    client = SecretClient(vault_url=key_vault, credential=credentials)
    try:
        return client.get_secret(secret_name)
    except HttpResponseError as ex:
        return None
