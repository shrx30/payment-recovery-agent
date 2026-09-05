\## 📖 Instruction Manual



\### 1. Install



python -m venv .venv

.venv\\Scripts\\activate

pip install -r requirements.txt



\### 2. Configure API Key



Create a `.env` file with the required NVIDIA API credentials.



Do not commit `.env`.



\### 3. Load Evaluation Data



python -m app.load\_eval\_data



\### 4. Run Demo



python demo.py



\### 5. Run Tests



python -m app.test\_signals



\### 6. Run Evaluation



python -m app.evaluate\_recovery

















\# AI Revenue Recovery Agent



> \*\*Turn failed payments into recoverable revenue — without blindly retrying payments.\*\*



An AI-powered payment recovery agent designed to identify failed payments that may still be recoverable, choose a safe intervention, execute it within bounded rules, verify the result, and escalate cases that should not be automated.



\## 🎯 Problem



Failed payments represent potential revenue leakage for businesses.



However, simply retrying every failed payment is unsafe. A timeout or ambiguous gateway response does not always tell us whether the payment was actually authorized. Blind retries can create duplicate-charge risk, while manually investigating every failure is slow and expensive.



The challenge is to \*\*recover as much legitimate revenue as possible while keeping financial actions safe and controlled.\*\*



\## 💡 Solution



This project implements a hybrid payment-recovery agent combining:



\- Deterministic policies for known failure conditions

\- LLM reasoning for ambiguous gateway responses

\- Signal extraction from gateway messages

\- Bounded action selection

\- Retry limits and safety rules

\- Execution and verification

\- Escalation when automation is not appropriate

\- Evaluation across 286 payment cases



The LLM does not directly control payment operations. It selects from actions already permitted by the recovery policy.



                         FAILED PAYMENT
                               |
                               v
                      SIGNAL EXTRACTION
                               |
                               v
                  EVIDENCE / POLICY CLASSIFICATION
                               |
                    +----------+----------+
                    |                     |
                    v                     v
             KNOWN FAILURE          AMBIGUOUS CASE
                    |                     |
                    v                     v
          DETERMINISTIC POLICY           LLM
                    |                 REASONING
                    +---------+-----------+
                              |
                              v
                     SAFETY CONSTRAINTS
                              |
                              v
                      EXECUTE RECOVERY
                              |
                              v
                       VERIFY OUTCOME
                              |
                    +---------+---------+
                    |                   |
                    v                   v
                 RECOVERED          ESCALATED