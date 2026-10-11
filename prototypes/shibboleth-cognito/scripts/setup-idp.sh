#!/usr/bin/env bash
# Generates the test university's keys, test users and SAML metadata. Run once before the first
# `docker compose up`; re-running keeps existing keys and users.
#
#   prototypes/shibboleth-cognito/scripts/setup-idp.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
CREDS="$HERE/idp/credentials"
META="$HERE/idp/metadata"
IMAGE="i2incommon/shib-idp:5.2.3_20260824_rocky9_multiarch"
ENTITY_ID="https://localhost:8443/idp/shibboleth"
BASE_URL="https://localhost:8443/idp"
mkdir -p "$CREDS" "$META"

# Fresh signing and encryption keys. The image ships keys anyone can download, so a Cognito pool
# that trusted them would accept forged sign-ins.
for use in signing encryption; do
  if [ ! -f "$CREDS/idp-$use.key" ]; then
    openssl req -x509 -newkey rsa:3072 -nodes -days 3650 -subj "/CN=localhost" \
      -keyout "$CREDS/idp-$use.key" -out "$CREDS/idp-$use.crt" 2>/dev/null
    echo "created idp-$use key"
  fi
done

# Test users (local only). Passwords are random and kept in test-users.txt, which git ignores.
if [ ! -f "$CREDS/test-users.txt" ]; then
  : > "$CREDS/demo.htpasswd"
  : > "$CREDS/test-users.txt"
  for user in alice bob; do
    password="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)"
    echo "$user:$(openssl passwd -apr1 "$password")" >> "$CREDS/demo.htpasswd"
    echo "$user $password" >> "$CREDS/test-users.txt"
  done
  chmod 600 "$CREDS/test-users.txt"
  echo "created test users alice and bob (passwords in idp/credentials/test-users.txt)"
fi

# The image's secrets file, plus a salt for persistent IDs (used from pass 2 on).
if [ ! -f "$CREDS/secrets.properties" ]; then
  docker run --rm --entrypoint cat "$IMAGE" /opt/shibboleth-idp/credentials/secrets.properties > "$CREDS/secrets.properties"
  echo "idp.persistentId.salt = $(openssl rand -base64 32)" >> "$CREDS/secrets.properties"
  chmod 600 "$CREDS/secrets.properties"
  echo "created secrets.properties"
fi

cert_body() { sed -e '/-----/d' "$1" | tr -d '\n'; }

# The IdP metadata a campus would hand us. NameID formats come from idp/nameid-formats.txt so a
# pass can advertise persistent IDs without editing this script.
FORMATS=""
while read -r f; do
  [ -n "$f" ] && FORMATS="$FORMATS    <NameIDFormat>$f</NameIDFormat>"$'\n'
done < "$HERE/idp/nameid-formats.txt"

cat > "$META/idp-metadata.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
                  xmlns:ds="http://www.w3.org/2000/09/xmldsig#"
                  xmlns:shibmd="urn:mace:shibboleth:metadata:1.0"
                  entityID="$ENTITY_ID">
  <IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <Extensions>
      <shibmd:Scope regexp="false">example.edu</shibmd:Scope>
    </Extensions>
    <KeyDescriptor use="signing">
      <ds:KeyInfo><ds:X509Data><ds:X509Certificate>$(cert_body "$CREDS/idp-signing.crt")</ds:X509Certificate></ds:X509Data></ds:KeyInfo>
    </KeyDescriptor>
    <KeyDescriptor use="encryption">
      <ds:KeyInfo><ds:X509Data><ds:X509Certificate>$(cert_body "$CREDS/idp-encryption.crt")</ds:X509Certificate></ds:X509Data></ds:KeyInfo>
    </KeyDescriptor>
$FORMATS    <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect" Location="$BASE_URL/profile/SAML2/Redirect/SSO"/>
    <SingleSignOnService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST" Location="$BASE_URL/profile/SAML2/POST/SSO"/>
  </IDPSSODescriptor>
</EntityDescriptor>
XML
echo "wrote idp/metadata/idp-metadata.xml"

# Placeholder until Terraform creates the pool; render-sp-metadata.sh replaces it.
[ -f "$META/cognito-sp.xml" ] || cat > "$META/cognito-sp.xml" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<EntitiesDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"/>
XML
