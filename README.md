# AI DataScout

AI DataScout is a Streamlit prototype for responsible data intelligence over public or otherwise authorized clinic-directory data. It demonstrates data cleaning, deduplication, data-quality reporting, filters, charts, CSV export, and optional AI summaries.

## Important data and compliance notes
- `sample_data.csv` is fictional demonstration data. `example.org` links are placeholders, not real clinics.
- Do not scrape Healthdirect listings without written permission or a permitted interface/feed. Review the current source terms, applicable privacy rules, and intellectual-property restrictions.
- `robots.txt` is a technical signal, not legal permission. This app's optional extractor checks it and fails closed if it cannot verify permission, but you must also review the source's terms.
- The optional extractor fetches only one page and does not crawl links. It is not enabled until the user confirms permission.
- Never upload patient records or sensitive health information.
- Use a monitored contact address in the user agent before any real authorized extraction.
- The optional LLM API receives up to 40 rows of the current filtered dataset. Use only data you are allowed to share with the chosen provider.

## Features
- CSV upload and fictional sample mode
- Column alias normalization and missing-value handling
- Deduplication by clinic name, suburb, and state
- State and text filters
- Data completeness metrics
- State distribution chart
- Local insights without API credentials
- Optional OpenAI-compatible Chat Completions request
- Cleaned CSV export
- Guarded one-page JSON-LD extraction for authorized sources

## Run locally
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Optional AI API
Set `OPENAI_API_KEY` as an environment variable or a Streamlit secret. Never commit keys to GitHub. The code uses the Chat Completions endpoint with `gpt-4o-mini`; check your account's model access and pricing before use. If no key is set or the API fails, local insights are shown instead.

For Streamlit Community Cloud, add a secret in the app's settings rather than committing `.streamlit/secrets.toml`. See Streamlit's secrets documentation.

## Tests
```bash
pytest -q
```

## Deployment
1. Create a GitHub repository and push the project files.
2. Check that no secrets, private datasets, or unlicensed data are included.
3. In Streamlit Community Cloud, create an app and select `app.py` as the entrypoint.
4. Add `OPENAI_API_KEY` through the deployment secrets UI only if you choose to enable the optional API.
5. Test the public URL in a private/incognito browser and verify that the demo data is clearly marked as fictional.

## Suggested next improvements
- Add a source registry with permission status, license URL, retrieval date, and attribution.
- Add CSV schema validation and downloadable data-quality report.
- Add explicit provenance and source-specific rate-limit settings for any approved source.
- Add pagination and caching only after confirming that the source permits the intended access pattern.
