// CloudFront Function (viewer-request): serve /services/ -> /services/index.html
// Needed only for the S3 + CloudFront route (Amplify Hosting handles this itself).
function handler(event) {
  var req = event.request;
  var uri = req.uri;
  if (uri.endsWith('/')) req.uri = uri + 'index.html';
  else if (!uri.includes('.')) req.uri = uri + '/index.html';
  return req;
}
