# SimpleInfra Features Roadmap

## Quick Wins (Priority 1 - In Progress)

These 5 features will be implemented first for maximum impact with reasonable effort.

### 1. Testing Framework ✅ NEXT

**Syntax:**
```simpleinfra
test "Web server is running":
    expect url "http://localhost:80" status 200
    expect file "/etc/nginx/nginx.conf" exists
    expect service "nginx" is_running
    expect port 80 is_open
    expect command "nginx -t" exit_code 0
```

**Implementation Plan:**
- [ ] Add Test AST nodes (TestStatement, ExpectStatement)
- [ ] Update grammar with test syntax
- [ ] Add transformer methods
- [ ] Create TestExecutor in engine/
- [ ] Add `si test` CLI command
- [ ] Create example test file

**Files to Modify:**
- `src/simpleinfra/ast/nodes.py` - Add Test nodes
- `src/simpleinfra/dsl/grammar.lark` - Add test grammar
- `src/simpleinfra/dsl/transformer.py` - Add test transformer
- `src/simpleinfra/engine/test_executor.py` - NEW FILE
- `src/simpleinfra/cli/app.py` - Add test command
- `examples/test_example.si` - NEW FILE

---

### 2. Better Error Messages

**Current:**
```
Error: Syntax error
```

**New:**
```
Error in deploy.si:42:5

  41 | task "Deploy" on web:
  42 |     instal nginx
       |     ^^^^^^
  43 |     start service nginx

Syntax error: Unknown action 'instal'
Did you mean: install?
```

**Implementation Plan:**
- [ ] Update SourceLocation tracking in parser
- [ ] Add suggestion engine for typos
- [ ] Color-code error output
- [ ] Show surrounding lines for context
- [ ] Add error recovery hints

**Files to Modify:**
- `src/simpleinfra/errors/parse_errors.py` - Enhanced errors
- `src/simpleinfra/errors/runtime_errors.py` - Better runtime errors
- `src/simpleinfra/cli/output.py` - Error formatting

---

### 3. Enhanced Conditionals

**New Syntax:**
```simpleinfra
set env "production"
set cpu_count 4

task "Configure" on web:
    # Comparison operators
    if env == "production":
        ensure port 443 is open

    if cpu_count > 2:
        run "systemctl set-property nginx CPUQuota=200%"

    # Multiple conditions
    if env == "production" and cpu_count >= 4:
        run "enable_high_performance_mode"

    if os is "ubuntu" or os is "debian":
        install nginx

    # Not equal
    if env != "development":
        run "setup_ssl"
```

**Implementation Plan:**
- [ ] Add ComparisonOperator enum (==, !=, >, <, >=, <=)
- [ ] Add LogicalOperator enum (and, or, not)
- [ ] Update Conditional AST node
- [ ] Update grammar for comparisons
- [ ] Update executor to evaluate complex conditions
- [ ] Add tests

**Files to Modify:**
- `src/simpleinfra/ast/nodes.py` - Update Conditional node
- `src/simpleinfra/dsl/grammar.lark` - Add comparison syntax
- `src/simpleinfra/dsl/transformer.py` - Parse comparisons
- `src/simpleinfra/engine/executor.py` - Evaluate conditions

---

### 4. Retry Logic

**Syntax:**
```simpleinfra
task "Deploy with Retry" on web:
    # Simple retry
    retry 3:
        run "curl https://api.example.com/deploy"

    # Retry with backoff
    retry 5 backoff exponential:
        run "docker pull myimage:latest"

    # Retry with custom delay
    retry 3 delay 5:
        run "wget https://releases.example.com/app.tar.gz"

    # On failure callback
    retry 3:
        run "critical_operation"
    on_retry:
        run "echo Retrying..."
        wait 2 seconds
    on_failure:
        notify slack "#alerts"
        run task "Rollback"
```

**Implementation Plan:**
- [ ] Add Retry AST node
- [ ] Add retry grammar
- [ ] Implement retry executor with backoff strategies
- [ ] Add on_retry and on_failure hooks
- [ ] Create examples

**Files to Modify:**
- `src/simpleinfra/ast/nodes.py` - Add Retry node
- `src/simpleinfra/dsl/grammar.lark` - Add retry syntax
- `src/simpleinfra/dsl/transformer.py` - Parse retry blocks
- `src/simpleinfra/engine/executor.py` - Execute with retry
- `src/simpleinfra/utils/retry.py` - Retry utilities

---

### 5. Functions/Macros

**Syntax:**
```simpleinfra
# Define reusable functions
function setup_webserver(domain, port=80, ssl=true):
    install nginx
    install certbot

    copy "nginx.conf" to "/etc/nginx/sites-available/{domain}"

    if ssl:
        certificate:
            action "obtain"
            domain "{domain}"

    run "ln -s /etc/nginx/sites-available/{domain} /etc/nginx/sites-enabled/"
    restart service nginx

# Use functions
task "Setup Sites" on web:
    setup_webserver("example.com", port=443, ssl=true)
    setup_webserver("test.com", port=8080, ssl=false)
    setup_webserver("blog.com")  # Uses defaults

# Functions with return values
function get_server_count():
    return 5

set server_count get_server_count()
```

**Implementation Plan:**
- [ ] Add Function AST node
- [ ] Add FunctionCall AST node
- [ ] Add function grammar
- [ ] Implement function registry
- [ ] Handle parameter passing and defaults
- [ ] Implement variable scoping
- [ ] Support return values

**Files to Modify:**
- `src/simpleinfra/ast/nodes.py` - Add Function nodes
- `src/simpleinfra/dsl/grammar.lark` - Add function syntax
- `src/simpleinfra/dsl/transformer.py` - Parse functions
- `src/simpleinfra/engine/function_registry.py` - NEW FILE
- `src/simpleinfra/engine/executor.py` - Call functions
- `src/simpleinfra/variables/resolver.py` - Function scope

---

## Implementation Priority

**Week 1:**
1. Testing Framework (Day 1-2)
2. Better Error Messages (Day 2-3)

**Week 2:**
3. Enhanced Conditionals (Day 4-5)
4. Retry Logic (Day 5-6)

**Week 3:**
5. Functions/Macros (Day 7-9)

---

## Success Criteria

### Testing Framework:
- [ ] Can write and run tests
- [ ] Tests pass/fail correctly
- [ ] Clear test output
- [ ] Examples work

### Better Error Messages:
- [ ] Shows line numbers
- [ ] Displays context
- [ ] Suggests corrections
- [ ] Color-coded

### Enhanced Conditionals:
- [ ] All comparison operators work
- [ ] Logical AND/OR work
- [ ] Examples demonstrate usage
- [ ] Documentation updated

### Retry Logic:
- [ ] Basic retry works
- [ ] Exponential backoff works
- [ ] Callbacks work
- [ ] Examples provided

### Functions/Macros:
- [ ] Can define functions
- [ ] Can call functions
- [ ] Parameters work
- [ ] Defaults work
- [ ] Scope is correct
- [ ] Examples demonstrate reuse

---

## Next Features (Priority 2)

After completing 1-5, tackle these:

6. **VSCode Extension** - Syntax highlighting, autocomplete
7. **State Management** - Track deployed resources
8. **Kubernetes Module** - K8s automation
9. **Parallel Execution** - Run tasks simultaneously
10. **Cloud Modules** - AWS, Azure, GCP basics

---

## Long-term Roadmap (Priority 3)

- Interactive mode
- Drift detection
- Cost estimation
- RBAC
- Audit logging
- Module marketplace
- CI/CD integrations

---

## Status: Ready to Implement

All 5 quick wins are scoped and ready for implementation. Each feature has:
- ✅ Clear syntax design
- ✅ Implementation plan
- ✅ Files to modify identified
- ✅ Success criteria defined

**Next Step:** Implement Testing Framework (Feature #1)
