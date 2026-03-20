# Green-tech_inventory_assistant

# 🌿 EcoTrack AI — Green-Tech Inventory Assistant

**Candidate Name:** *Sophia Ann Chikkala*

**Scenario Chosen:** AI-Powered Green-Tech Inventory Assistant

**Estimated Time Spent:** ~8 hours across design, implementation, debugging, and testing

**Video Walkthrough:** *https://youtu.be/CEPTLfCGTTo*

---

## Quick Start

### Prerequisites
- Python 3.10+
- Groq API key — free at [console.groq.com](https://console.groq.com)

### Run Commands

```bash
git clone <repo-url>
cd ecotrack

pip install -r requirements.txt

# Add your key to .env:  GROQ_API_KEY=your_key_here

python data/generate_synthetic_data.py   # creates inventory.json + usage_history.json
streamlit run app/main.py
```

### Test Commands

```bash
python tests/test_ecotrack.py
# Expected: Results: 39 passed, 0 failed
```

No pytest required. Plain Python, zero test dependencies.

---

## AI Disclosure

**Did you use an AI assistant?** Yes, Claude was used throughout development.

**How did you verify the suggestions?**
Every suggestion was run, tested, and read before being accepted. The forecasting logic (WMA, FIFO waste calculation, zero-day exclusion) was verified by writing unit tests against known inputs and checking the outputs manually. The alert routing logic was traced through by hand for each of the four alert types. UI code was verified by running the app and clicking through every flow.

**One example of a suggestion rejected or changed:**
The initial simulation loop checked for item expiry at the *start* of each day before depletion ran. This meant that on expiry day+1, the waste quantity was calculated from the pre-usage stock level. The fix was to reverse the order: run depletion first, then check expiry at the end of the day so the waste figure reflects actual leftover stock. The original suggestion was rejected and the correct ordering implemented and verified with a targeted test.


## Tradeoffs & Prioritisation

**What was cut to stay within the time limit?**

- **Computer vision / shelf scanning** — photo-to-inventory-count was considered and explicitly excluded. Implementation risk was too high (model selection, image preprocessing, count extraction accuracy) for the time available. Live Mode's manual count entry covers the same user need with zero error rate.
- **Carbon impact score** — the sustainability panel shows ₹ waste value which covers the waste-reduction metric, but a true CO₂e score requires category-specific emission factors. Noted as a future enhancement.
- **Database** — JSON flat files were chosen deliberately. The interface is fully abstracted so migration is a two-function change, but adding a DB during the build would have cost time with no visible user-facing improvement at demo scale.
- **Email/SMS alerts** — the alert system is complete inside the app but does not push notifications outside it.

**What would be built next with more time?**
- **SQLite persistence** — drop-in replacement behind `inventory.py`, eliminates concurrent-write race condition for multi-user deployments
- **Carbon impact score** — kg CO₂e saved by reducing waste, using category-specific emission factors (food, chemicals, paper)
- **Visual shelf scanning** — photo input → item identification and count extraction via vision model
- **Scheduled daily brief** — email or SMS delivery of the daily intelligence brief outside the app
- **Supplier API integration** — live pricing from local sustainable suppliers rather than LLM-generated suggestions
- **Multi-user access control** — org-level authentication so café staff see only café inventory


**Known limitations**

- **Concurrent writes** — JSON persistence has a last-write-wins race condition if multiple Streamlit sessions write simultaneously. Acceptable for single-user demo use; SQLite would fix this.
- **Simulation is one-directional** — simulating forward then resetting to original state is supported, but there is no partial undo. A step-back feature would require snapshot history.
- **WMA requires history** — new items fall back to rule-based estimates until 3+ non-zero usage days are recorded. The confidence label communicates this clearly but the forecast is less precise on new items.
- **LLM advice is not verified** — supplier suggestions are generated text, not live data. They are clearly labelled and should be treated as starting points, not authoritative sources.
- **Org patterns are fixed** — weekend closure probabilities are hardcoded in the data generator. Real-world use would benefit from org-configurable calendar settings.
