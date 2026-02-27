# API Endpoint Test Report

```json
{
  "report_generated_at_utc": "2026-02-27T07:34:04Z",
  "execution_status": "completed_with_blockers",
  "input_api_details": {
    "base_url": "https://yourdomain.com/api/",
    "endpoint": "/your-endpoint/",
    "resolved_url": "https://yourdomain.com/api/your-endpoint/",
    "method_requested": "GET or POST",
    "headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer <token>"
    },
    "body_if_post": {
      "field1": "value",
      "field2": "value"
    }
  },
  "execution_results": {
    "attempt_1_powershell_invoke_webrequest": {
      "get": {
        "status_code": null,
        "response_headers": null,
        "response_body": null,
        "error": {
          "type": "System.Net.WebException",
          "message": "The underlying connection was closed: Could not establish trust relationship for the SSL/TLS secure channel."
        }
      },
      "post": {
        "status_code": null,
        "response_headers": null,
        "response_body": null,
        "error": {
          "type": "System.Net.WebException",
          "message": "The underlying connection was closed: Could not establish trust relationship for the SSL/TLS secure channel."
        }
      }
    },
    "attempt_2_curl_with_insecure_tls": {
      "get": {
        "status_code": 301,
        "response_headers": {
          "Date": "Fri, 27 Feb 2026 07:34:04 GMT",
          "Content-Type": "text/html; charset=UTF-8",
          "Content-Length": "0",
          "Connection": "keep-alive",
          "X-Sucuri-ID": "19002",
          "X-XSS-Protection": "1; mode=block",
          "X-Frame-Options": "SAMEORIGIN",
          "X-Content-Type-Options": "nosniff",
          "Content-Security-Policy": "upgrade-insecure-requests;",
          "Expires": "Thu, 19 Nov 1981 08:52:00 GMT",
          "Cache-Control": "no-store, no-cache, must-revalidate",
          "Pragma": "no-cache",
          "Set-Cookie": "sessions=7spvn32q5ig9kgebt5o822uspv0p0mau; expires=Fri, 27-Feb-2026 09:34:04 GMT; Max-Age=7200; path=/; domain=.bedpage.com; HttpOnly; SameSite=Lax",
          "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
          "Location": "https://www.bedpage.com/404",
          "Access-Control-Allow-Origin": "https://*.yourdomain.com",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS, DELETE, PUT",
          "Access-Control-Allow-Headers": "Content-Type, Authorization",
          "Content-Encoding": "gzip",
          "Server": "Sucuri/Cloudproxy",
          "X-Sucuri-Cache": "BYPASS",
          "Alt-Svc": "h3=\":443\"; ma=2592000, h3-29=\":443\"; ma=2592000"
        },
        "response_body": ""
      },
      "post": {
        "status_code": 403,
        "response_headers": {
          "Date": "Fri, 27 Feb 2026 07:34:03 GMT",
          "Content-Type": "text/html",
          "Transfer-Encoding": "chunked",
          "Connection": "keep-alive",
          "X-Sucuri-ID": "19002",
          "X-XSS-Protection": "1; mode=block",
          "X-Frame-Options": "SAMEORIGIN",
          "X-Content-Type-Options": "nosniff",
          "Content-Security-Policy": "upgrade-insecure-requests;",
          "X-Sucuri-Block": "FBP007",
          "Server": "Sucuri/Cloudproxy"
        },
        "response_body": "<!DOCTYPE html>\\n<html lang=\"en\" xmlns=\"http://www.w3.org/1999/xhtml\">\\n<head>\\n<link rel=\"stylesheet\" href=\"https://cdn.sucuri.net/sucuri-firewall-block.css\" />\\n<section class=\"center clearfix\">\\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />\\n<title>Sucuri WebSite Firewall - Access Denied</title>\\n<link href=\"https://fonts.googleapis.com/css?family=Open+Sans:400,300,600,700\" rel=\"stylesheet\" type=\"text/css\">\\n</head>\\n<body>\\n<div id=\"main-container\">\\n<header class=\"app-header clearfix\">\\n<div class=\"wrap\">\\n<a href=\"https://www.sucuri.net/?utm_source=firewall_block\" class=\"logo\"></a>\\n<span class=\"logo-neartext\">Website Firewall</span>\\n<a href=\"https://sucuri.net/?utm_source=firewall_block\" class=\"site-link\">Back to sucuri.net</a>\\n</div>\\n</header>\\n\\n<section class=\"app-content access-denied clearfix\"><div class=\"box center width-max-940\"><h1 class=\"brand-font font-size-xtra no-margin\"><i class=\"icon-circle-red\"></i>Access Denied - Sucuri Website Firewall</h1>\\n<p class=\"medium-text code-snippet\">If you are the site owner (or you manage this site), please whitelist your IP or if you think this block is an error please <a href=\"https://support.sucuri.net/?utm_source=firewall_block\" class=\"color-green underline\">open a support ticket</a> and make sure to include the block details (displayed in the box below), so we can assist you in troubleshooting the issue. </p><h2>Block details:</h1>\\n<table class=\"property-table overflow-break-all line-height-16\">\\n<tr>\\n<td>Your IP:</td>\\n<td><span>43.224.0.209</span></td>\\n</tr>\\n<tr><td>URL:</td>\\n<td><span>yourdomain.com/api/your-endpoint/</span></td>\\n</tr>\\n<tr>\\n<td>Your Browser: </td>\\n<td><span>curl/8.16.0</span></td>\\n</tr>\\n<tr><td>Block ID:</td>\\n<td><span>FBP007</span></td>\\n</tr>\\n<tr>\\n<td>Block reason:</td>\\n<td><span>Fake bot access.</span></td>\\n</tr>\\n<tr>\\n<td>Time:</td>\\n<td><span>2026-02-27 02:34:03</span></td>\\n</tr>\\n<tr>\\n<td>Server ID:</td>\\n<td><span>19002</span></td></tr>\\n</table>\\n</div>\\n</section>\\n\\n<footer>\\n<span>&copy; 2026 Sucuri Inc. All rights reserved.</span>\\n<span id=\"privacy-policy\"><a href=\"https://sucuri.net/privacy-policy?utm_source=firewall_block\" target=\"_blank\" rel=\"nofollow noopener\">Privacy</a></span>\\n</footer>\\n</div>\\n</body>\\n</html>",
        "transport_note": "curl also reported: URL rejected: Port number was not a decimal number between 0 and 65535."
      }
    }
  },
  "requested_output_items": {
    "status_code": {
      "get": 301,
      "post": 403
    },
    "response_headers": {
      "get": "captured",
      "post": "captured"
    },
    "response_body_formatted_json": {
      "available": false,
      "reason": "Endpoint returned redirect (301) and HTML/WAF block page (403), not JSON."
    },
    "required_fields": [
      {
        "field": "Authorization",
        "required": true,
        "type": "string",
        "format": "Bearer <access_token>"
      },
      {
        "field": "Content-Type",
        "required": true,
        "type": "string",
        "allowed": [
          "application/json"
        ]
      },
      {
        "field": "field1",
        "required": "unknown (not verifiable on blocked endpoint)",
        "type": "string"
      },
      {
        "field": "field2",
        "required": "unknown (not verifiable on blocked endpoint)",
        "type": "string"
      }
    ],
    "optional_fields": [
      {
        "field": "query params / pagination params",
        "required": "unknown",
        "type": "unknown"
      }
    ],
    "data_types": {
      "request_headers.Authorization": "string",
      "request_headers.Content-Type": "string",
      "request_body.field1": "string",
      "request_body.field2": "string",
      "response": "non-JSON HTML in current test"
    }
  },
  "authentication": {
    "required": true,
    "bearer_token_format": "Authorization: Bearer <token>",
    "required_headers": {
      "Content-Type": "application/json",
      "Authorization": "Bearer <token>"
    }
  },
  "pagination": {
    "exists": "unknown",
    "page_structure": null,
    "total_count": null,
    "next": null,
    "previous": null,
    "note": "Could not inspect pagination because no JSON payload was returned."
  },
  "validation_error": {
    "observed": false,
    "error_response_format": {
      "example_standard_format": {
        "message": "Validation failed",
        "errors": {
          "field1": [
            "This field is required."
          ],
          "field2": [
            "This field is required."
          ]
        }
      },
      "note": "Actual format could not be confirmed from this endpoint run."
    }
  },
  "role_based_response": {
    "supported_role_tests": [
      "SuperAdmin",
      "Admin",
      "Seller",
      "Buyer"
    ],
    "SuperAdmin": {
      "tested": false,
      "response": null,
      "reason": "No valid token + endpoint returned non-application JSON response."
    },
    "Admin": {
      "tested": false,
      "response": null,
      "reason": "No valid token + endpoint returned non-application JSON response."
    },
    "Seller": {
      "tested": false,
      "response": null,
      "reason": "No valid token + endpoint returned non-application JSON response."
    },
    "Buyer": {
      "tested": false,
      "response": null,
      "reason": "No valid token + endpoint returned non-application JSON response."
    }
  },
  "example_requests": {
    "web_axios": "import axios from 'axios';\\n\\nconst url = 'https://yourdomain.com/api/your-endpoint/';\\nconst token = '<token>';\\n\\nconst headers = {\\n  'Content-Type': 'application/json',\\n  Authorization: `Bearer ${token}`\\n};\\n\\n// GET\\nconst getRes = await axios.get(url, { headers });\\nconsole.log(getRes.status, getRes.headers, getRes.data);\\n\\n// POST\\nconst payload = { field1: 'value', field2: 'value' };\\nconst postRes = await axios.post(url, payload, { headers });\\nconsole.log(postRes.status, postRes.headers, postRes.data);",
    "mobile_fetch_api": "const url = 'https://yourdomain.com/api/your-endpoint/';\\nconst token = '<token>';\\n\\nconst headers = {\\n  'Content-Type': 'application/json',\\n  Authorization: `Bearer ${token}`\\n};\\n\\n// GET\\nconst getResp = await fetch(url, { method: 'GET', headers });\\nconst getData = await getResp.json();\\nconsole.log(getResp.status, getData);\\n\\n// POST\\nconst postResp = await fetch(url, {\\n  method: 'POST',\\n  headers,\\n  body: JSON.stringify({ field1: 'value', field2: 'value' })\\n});\\nconst postData = await postResp.json();\\nconsole.log(postResp.status, postData);",
    "curl": "curl -i -X POST 'https://yourdomain.com/api/your-endpoint/' \\\\\\n  -H 'Content-Type: application/json' \\\\\\n  -H 'Authorization: Bearer <token>' \\\\\\n  -d '{\"field1\":\"value\",\"field2\":\"value\"}'"
  },
  "missing_required_fields": [
    "Real API domain (current host appears placeholder/parking and WAF-protected).",
    "Confirmed single HTTP method to validate (GET or POST).",
    "Valid Bearer token for target API.",
    "Actual endpoint schema (required vs optional request fields).",
    "Role-specific tokens/credentials for SuperAdmin/Admin/Seller/Buyer test matrix."
  ]
}
```

