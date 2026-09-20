#!/usr/bin/env bash
# Deploy site/ to S3 + CloudFront. Fill in the two variables once. Requires: aws CLI configured.
set -euo pipefail
BUCKET="${BUCKET:-uracquet-v2}"                 # S3 bucket name (create once; private, CloudFront OAC in front)
DIST_ID="${DIST_ID:-}"                          # CloudFront distribution ID (optional; skips invalidation if empty)
cd "$(dirname "$0")"
python3 build.py
# HTML: short cache so edits show quickly; images/CSS: long cache
aws s3 sync site/ "s3://$BUCKET" --delete --exclude "img/*" --exclude "style.css" --cache-control "public, max-age=300"
aws s3 sync site/img/ "s3://$BUCKET/img/" --delete --cache-control "public, max-age=31536000, immutable"
aws s3 cp site/style.css "s3://$BUCKET/style.css" --cache-control "public, max-age=86400"
if [ -n "$DIST_ID" ]; then aws cloudfront create-invalidation --distribution-id "$DIST_ID" --paths "/*" >/dev/null && echo "invalidated $DIST_ID"; fi
echo "deployed to s3://$BUCKET"
