# Deploy Koyla AI on Render

1. Push this folder (the one containing `Dockerfile`) to a new GitHub repo.
2. Render > New > Blueprint > select the repo > Apply. (`render.yaml` sets Docker, Singapore region, Standard plan = 2 GB RAM, 5 GB disk at /data, health check /healthz.)
3. Wait for the first build (several minutes: it bakes in the OCR + embedding models). Logs should end with "Application startup complete".
4. Open the URL. Dashboard should show 11 documents / 7,717 facts (seeded from `seed/` on first boot).
5. Upload a PDF; Documents tab should go queued > processing > validated.

Do NOT use Free/Starter (512 MB): OCR peaked at ~1.3 GB in testing.
LLM is disabled on Render (LLM_PROVIDER=none): answers are extractive with citations.
