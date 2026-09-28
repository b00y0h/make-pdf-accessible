variable "name" {
  description = "Name prefix for the CloudFront distribution, function, policies and OAC (letters, digits, hyphens)"
  type        = string
}

variable "bucket_name" {
  description = "Globally unique name of the private S3 bucket that holds the exported site"
  type        = string
}

variable "comment" {
  description = "Comment shown on the CloudFront distribution"
  type        = string
  default     = "Static site"
}

variable "primary_domain" {
  description = "Canonical host name of the site (redirect target for redirect_hosts and extensionless paths)"
  type        = string
}

variable "aliases" {
  description = "Alternate domain names served by the distribution (must be covered by certificate_arn)"
  type        = list(string)
}

variable "redirect_hosts" {
  description = "Host names that receive a 301 redirect to primary_domain (for example the www host)"
  type        = list(string)
  default     = []
}

variable "certificate_arn" {
  description = "ARN of an ACM certificate in us-east-1 covering every alias"
  type        = string
}

variable "web_acl_arn" {
  description = "ARN of a CLOUDFRONT-scoped WAFv2 web ACL to associate, or null for none"
  type        = string
  default     = null
}

variable "log_bucket_domain_name" {
  description = "Bucket domain name for CloudFront standard logs, or null to disable logging"
  type        = string
  default     = null
}

variable "log_prefix" {
  description = "Prefix for CloudFront standard log objects"
  type        = string
  default     = "static-site/"
}

variable "price_class" {
  description = "CloudFront price class"
  type        = string
  default     = "PriceClass_100"
}

variable "default_root_object" {
  description = "Object served for the root path"
  type        = string
  default     = "index.html"
}

variable "error_page_path" {
  description = "Path of the static 404 page returned for missing objects (Next.js export writes /404.html)"
  type        = string
  default     = "/404.html"
}

variable "api_origin" {
  description = "Origin (scheme and host) of the platform API that browser code may call; added to CSP connect-src and form-action"
  type        = string
  default     = ""
}

variable "extra_connect_src" {
  description = "Additional CSP connect-src origins (analytics collector, CAPTCHA verification)"
  type        = list(string)
  default     = []
}

variable "extra_frame_src" {
  description = "Additional CSP frame-src origins (CAPTCHA widget); empty means frame-src 'none'"
  type        = list(string)
  default     = []
}

variable "extra_script_src" {
  description = "Additional CSP script-src origins (CAPTCHA or analytics scripts)"
  type        = list(string)
  default     = []
}

variable "content_security_policy" {
  description = "Full Content-Security-Policy value to use instead of the generated one, or null to generate"
  type        = string
  default     = null
}

variable "tags" {
  description = "Tags applied to every taggable resource"
  type        = map(string)
  default     = {}
}
