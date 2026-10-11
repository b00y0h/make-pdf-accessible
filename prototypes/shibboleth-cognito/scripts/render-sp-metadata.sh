#!/usr/bin/env bash
# Writes Cognito's service-provider metadata for the test university from Terraform outputs.
# Cognito's entity ID and response URL are what a campus enters for us.
#
#   AWS_PROFILE=pdf-dev prototypes/shibboleth-cognito/scripts/render-sp-metadata.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
(cd "$HERE/terraform" && terraform output -json > outputs.json)
read -r ENTITY_ID ACS_URL < <(python3 -I -c '
import json, sys
o = json.load(open(sys.argv[1]))
print(o["sp_entity_id"]["value"], o["acs_url"]["value"])
' "$HERE/terraform/outputs.json")

# With encrypted responses on, Cognito publishes a certificate the campus encrypts assertions to.
read -r POOL_ID PROVIDER < <(python3 -I -c '
import json, sys
o = json.load(open(sys.argv[1]))
print(o["user_pool_id"]["value"], o["provider_name"]["value"])
' "$HERE/terraform/outputs.json")
ENC_CERT="$(aws cognito-idp describe-identity-provider --region us-east-1 --user-pool-id "$POOL_ID" \
  --provider-name "$PROVIDER" --query 'IdentityProvider.ProviderDetails.ActiveEncryptionCertificate' --output text)"
KEY_DESCRIPTOR=""
if [ -n "$ENC_CERT" ] && [ "$ENC_CERT" != "None" ]; then
  KEY_DESCRIPTOR="    <KeyDescriptor use=\"encryption\">
      <ds:KeyInfo><ds:X509Data><ds:X509Certificate>$(echo "$ENC_CERT" | sed -e '/-----/d' | tr -d '\n ')</ds:X509Certificate></ds:X509Data></ds:KeyInfo>
      <!-- Cognito rejects Shibboleth's default AES-GCM (pass 3); advertising CBC makes the IdP use it -->
      <EncryptionMethod Algorithm=\"http://www.w3.org/2001/04/xmlenc#aes256-cbc\"/>
      <EncryptionMethod Algorithm=\"http://www.w3.org/2001/04/xmlenc#aes128-cbc\"/>
      <EncryptionMethod Algorithm=\"http://www.w3.org/2001/04/xmlenc#rsa-oaep-mgf1p\"/>
    </KeyDescriptor>"
fi

cat > "$HERE/idp/metadata/cognito-sp.xml" <<XML
<?xml version="1.0" encoding="UTF-8"?>
<EntityDescriptor xmlns="urn:oasis:names:tc:SAML:2.0:metadata"
                  xmlns:ds="http://www.w3.org/2000/09/xmldsig#" entityID="$ENTITY_ID">
  <SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
$KEY_DESCRIPTOR
    <!-- Cognito names users after the NameID and caps usernames at 128 characters, so ask for a
         stable, short persistent ID. Cognito's own requests don't specify a format. -->
    <NameIDFormat>urn:oasis:names:tc:SAML:2.0:nameid-format:persistent</NameIDFormat>
    <AssertionConsumerService Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                              Location="$ACS_URL" index="1"/>
  </SPSSODescriptor>
</EntityDescriptor>
XML
echo "wrote idp/metadata/cognito-sp.xml for $ENTITY_ID"
