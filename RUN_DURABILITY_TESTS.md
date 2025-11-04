# Running Durability Tests with Mocks

## 🚀 Quick Start

Run all durability tests with a single command:

```bash
./test_durability.sh
```

This script will:
1. ✅ Check prerequisites (venv, pytest, PostgreSQL)
2. ✅ Verify configurations (mocks enabled, durability enabled)
3. ✅ Setup database schema if needed
4. ✅ Run all 13 durability tests with mocks
5. ✅ Show detailed results and statistics

## 📋 What Gets Tested

The script runs all durability tests using mock agents:

### Checkpoint Creation
- ✅ Verifies checkpoints are saved during normal execution

### Email Collection Failures
- ✅ Tests checkpoint on email collection failure
- ✅ Tests resume after fixing email failure

### Slack Collection Failures
- ✅ Tests checkpoint before slack failure
- ✅ Tests resume skips already-completed steps

### Summarization Failures
- ✅ Tests resume from mid-workflow failure

### Multiple Failures
- ✅ Tests multiple failure/resume cycles

### Data Integrity
- ✅ Verifies checkpoint data is valid

### Integration
- ✅ Tests complete end-to-end workflow
- ✅ Validates mock data structure

### Performance
- ✅ Ensures mocks execute quickly (<30s)

### Configuration
- ✅ Validates mock configuration loads
- ✅ Validates all scenarios are defined

## 🎯 Expected Output

When all tests pass:

```
╔═══════════════════════════════════════════════════════════════════════╗
║        Durability Test Suite - Mock Agents                           ║
║        Testing Checkpoint/Resume Functionality                        ║
╚═══════════════════════════════════════════════════════════════════════╝

[1/6] Checking Prerequisites...
✓ Virtual environment exists
✓ Virtual environment activated
✓ pytest installed

[2/6] Verifying PostgreSQL...
✓ PostgreSQL is running
✓ PostgreSQL connection successful

[3/6] Verifying Test Configuration...
✓ Mock configuration exists
✓ Durability configuration exists
✓ Mocks are enabled
✓ Durability is enabled

[4/6] Setting Up Database Schema...
✓ Database schema exists

[5/6] Running Durability Tests...

tests/test_checkpoint_resume.py::TestCheckpointCreation::test_checkpoints_created_on_success PASSED
tests/test_checkpoint_resume.py::TestEmailCollectionFailure::test_email_collection_failure_creates_checkpoint PASSED
tests/test_checkpoint_resume.py::TestEmailCollectionFailure::test_email_collection_resume_after_failure PASSED
tests/test_checkpoint_resume.py::TestSlackCollectionFailure::test_slack_collection_failure_creates_checkpoint PASSED
tests/test_checkpoint_resume.py::TestSlackCollectionFailure::test_slack_collection_resume_skips_email PASSED
tests/test_checkpoint_resume.py::TestSummarizationFailures::test_email_summarization_failure_and_resume PASSED
tests/test_checkpoint_resume.py::TestMultipleFailures::test_multiple_failures_multiple_resumes PASSED
tests/test_checkpoint_resume.py::TestCheckpointData::test_checkpoint_contains_state_data PASSED
tests/test_checkpoint_resume.py::TestEndToEndWithMocks::test_complete_workflow_with_mocks PASSED
tests/test_checkpoint_resume.py::TestEndToEndWithMocks::test_mock_data_is_realistic PASSED
tests/test_checkpoint_resume.py::TestMockPerformance::test_mocks_execute_quickly PASSED
tests/test_checkpoint_resume.py::TestMockConfiguration::test_mock_config_loads_correctly PASSED
tests/test_checkpoint_resume.py::TestMockConfiguration::test_all_scenarios_are_defined PASSED

============================== 13 passed in 42.15s ==============================

[6/6] Test Summary

╔═══════════════════════════════════════════════════════════════════════╗
║                    ✅ ALL TESTS PASSED! ✅                             ║
╚═══════════════════════════════════════════════════════════════════════╝

Durability verification complete!

What was tested:
  ✅ Checkpoint creation during workflow execution
  ✅ Email collection failure and resume
  ✅ Slack collection failure and resume
  ✅ Summarization failure and resume
  ✅ Multiple failure/resume cycles
  ✅ Checkpoint data integrity
  ✅ Mock data realism
  ✅ Performance with mocks

Database Statistics:
  • Total checkpoints created: 156
  • Unique workflows tested: 13

✅ Durability tests completed successfully!
```

## 🔧 Prerequisites

The script automatically checks for:

1. **Virtual Environment**: `venv/` directory must exist
2. **PostgreSQL**: Running via docker-compose
3. **Dependencies**: pytest, psycopg, langgraph-checkpoint-postgres
4. **Configuration**: Mock and durability configs must exist

If anything is missing, the script will tell you what to do.

## 📊 Manual Alternatives

If you prefer to run tests manually:

### Run All Tests
```bash
source venv/bin/activate
pytest tests/test_checkpoint_resume.py -v
```

### Run Specific Test Category
```bash
# Email failures
pytest tests/test_checkpoint_resume.py::TestEmailCollectionFailure -v

# Slack failures
pytest tests/test_checkpoint_resume.py::TestSlackCollectionFailure -v

# Integration
pytest tests/test_checkpoint_resume.py::TestEndToEndWithMocks -v
```

### Run Single Test
```bash
pytest tests/test_checkpoint_resume.py::TestSlackCollectionFailure::test_slack_collection_resume_skips_email -v
```

### With Coverage
```bash
pytest tests/ --cov=framework --cov=app --cov-report=html
open htmlcov/index.html
```

## 🔍 Inspecting Results

### View Checkpoints in Database
```bash
# See all checkpoints
docker-compose exec postgres psql -U postgres -d langgraph -c \
  "SELECT thread_id, checkpoint_ns FROM checkpoints LIMIT 10;"

# Count checkpoints
docker-compose exec postgres psql -U postgres -d langgraph -c \
  "SELECT COUNT(*) FROM checkpoints;"

# Find interrupted workflows
docker-compose exec postgres psql -U postgres -d langgraph -c \
  "SELECT DISTINCT thread_id FROM checkpoints 
   WHERE thread_id NOT IN (
     SELECT thread_id FROM checkpoints WHERE checkpoint_ns LIKE '%__end__'
   );"
```

### View Test Logs
```bash
# Run with more verbose output
pytest tests/test_checkpoint_resume.py -vv -s

# Show captured output
pytest tests/test_checkpoint_resume.py -v --capture=no
```

## 🐛 Troubleshooting

### PostgreSQL Not Running
```bash
# Start PostgreSQL
docker-compose up -d postgres

# Check status
docker ps | grep postgres

# View logs
docker-compose logs postgres
```

### Missing Dependencies
```bash
# Install all dependencies
pip install -r requirements.txt

# Install test dependencies specifically
pip install pytest pytest-cov
```

### Configuration Issues
```bash
# Check mock config
cat config/mock_config.yaml

# Check durability config  
cat config/durability_config.yaml

# Ensure mocks and durability are enabled
grep "enabled:" config/mock_config.yaml config/durability_config.yaml
```

### Database Schema Issues
```bash
# Recreate schema
python framework/setup_postgres.py

# Or reset database
docker-compose down -v
docker-compose up -d postgres
sleep 5
python framework/setup_postgres.py
```

### Tests Hanging
```bash
# Run with timeout
pytest tests/test_checkpoint_resume.py -v --timeout=60

# Stop on first failure
pytest tests/test_checkpoint_resume.py -v -x
```

## 🎯 Test Scenarios

The tests use these scenarios from `config/mock_config.yaml`:

| Scenario | What Fails | Purpose |
|----------|------------|---------|
| `default` | Nothing | Normal execution |
| `email_collection_failure` | Email collector | Test early checkpoint |
| `slack_collection_failure` | Slack collector | Test mid-workflow checkpoint |
| `email_summarization_failure` | Email summarizer | Test late checkpoint |
| `multiple_failures` | Multiple points | Test retry logic |

## 📚 Additional Resources

- **Full Test Guide**: See `TESTING_GUIDE.md`
- **Mock Guide**: See `MOCK_AGENTS_GUIDE.md`
- **Test Scenarios**: See `TEST_SCENARIOS.md`
- **Interactive Demo**: Run `python example_mock_test.py`

## ✅ Success Criteria

Tests are passing when:
- ✅ All 13 tests show `PASSED`
- ✅ No errors or exceptions
- ✅ Checkpoints are created in PostgreSQL
- ✅ Interrupted workflows are detected and resumed
- ✅ Mock data flows through the workflow correctly

## 🚀 Next Steps

After tests pass:

1. **Try Manual Testing**
   ```bash
   python example_mock_test.py
   ```

2. **Run with Real Agents** (optional)
   - Edit `config/mock_config.yaml`: set `enabled: false`
   - Add credentials (credentials.json, slack_credentials.json)
   - Run: `python main.py`

3. **View Traces in Jaeger** (optional)
   ```bash
   ./start_with_tracing.sh
   # Open http://localhost:16686
   ```

4. **Monitor Database**
   ```bash
   # Use pgAdmin
   # Open http://localhost:5050
   # Login: admin@admin.com / admin
   ```

## 📝 Summary

The `test_durability.sh` script provides a complete, automated way to verify that your durable execution system works correctly using mock agents. No manual setup required - just run the script and it handles everything!

