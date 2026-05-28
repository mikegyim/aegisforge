package kubernetes.admission

test_denied_when_no_memory_limit {
  deny["container web must define memory limit"] with input as {
    "request": {
      "kind": {"kind": "Pod"},
      "object": {"spec": {"containers": [{"name": "web", "resources": {}}]}}
    }
  }
}

test_allowed_when_all_set {
  count(deny) == 0 with input as {
    "request": {
      "kind": {"kind": "Pod"},
      "object": {"spec": {"containers": [{
        "name": "web",
        "resources": {"limits": {"memory": "256Mi", "cpu": "500m"}},
        "securityContext": {"runAsNonRoot": true}
      }]}}
    }
  }
}
