import { defineConfig } from '@playwright/test';
export default defineConfig({
 testDir:'e2e',workers:1,timeout:120000,expect:{timeout:30000},
 use:{baseURL:'http://127.0.0.1:4200',browserName:'chromium',trace:'retain-on-failure'},
 webServer:[
  {command:'uv run --all-extras uvicorn backend.main:app --host 127.0.0.1 --port 8000',cwd:'..',url:'http://127.0.0.1:8000/api/v1/health',timeout:120000,env:{GEMINI_API_KEY:''}},
  {command:'npm start',url:'http://127.0.0.1:4200',timeout:300000}
 ]
});
