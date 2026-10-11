# GitHub Actions OIDC identity provider. IAM allows one provider per URL per account, so it lives
# here and each environment's deploy roles (infra/terraform/github_oidc.tf) look it up.
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    "6938fd4d98bab03faadb97b34396831e3780aea1",
    "1c58a3a8518e8759bf075b76b750d4f2df264fcd"
  ]

  tags = {
    Name = "${local.name_prefix}-github-oidc-provider"
  }
}
