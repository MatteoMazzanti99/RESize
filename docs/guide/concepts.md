# How to read the results

Every technology follows the same pattern: a few steps where you give the inputs, then a
results page.

## The results page

The page has two halves.

- **Left: the report.** It starts with **In short**, the key numbers and a one-sentence
  verdict. Then the pictures, the **design checks** sorted by importance, the detailed tables
  and the inputs.
- **Right: Why? Understand each step.** Pick a step to see its formula, the reasoning, the
  assumptions and your own numbers substituted in. The *Ask the tutor about this step* button
  sends that question to the AI tutor.

Next to the input fields a round **?** button opens the same explanation before you even
compute the result.

![Results page](../screenshots/pv_results.png)

## Design checks

Each check is a rule of thumb applied to your numbers, labelled **error** (the design does not
work), **warning** (probably wrong or risky), **note** (worth knowing) or **ok**. Every check
points to the *Why?* topic that explains it. They are deterministic and work offline.

## Costs, savings and sensitivity

Photovoltaic, wind, hydrogen, battery and solar thermal flows have a *costs* step. From it they
compute the cost of energy (LCOE or similar), simple and discounted payback, net present value
and avoided CO2 with a constant-price annuity model: no taxes, incentives or financing. The
prices are round placeholders; replace them with quotes.

Most results then show two pictures that answer *"what if my numbers are wrong?"*: a ranking
of which input moves the result most (each moved by 20 %), and curves of the result as each
input changes. If the net present value changes sign inside the range, the decision is fragile
for that input.

## Report

**Save the report as PDF** writes the page you see, in a light version, with the charts and
the formulas used.

## Projects

**Save project** (Ctrl+S) writes a small `.resize` file with every value of every step and,
if you downloaded it, the real hourly weather. **Open a saved project** (Ctrl+O) brings you
straight to its results. The files are plain JSON.

## AI tutor (optional)

**Ask the AI tutor...** opens a chat that knows your inputs, results and checks. It explains
the reasoning and may ask a question to check your understanding. You can use your own
Anthropic or OpenAI-compatible key, a local model with Ollama, or copy the project summary
into any chatbot. Your project values go only to the provider you choose. AI answers can be
wrong: the formulas in the *Why?* panel are the reference.
