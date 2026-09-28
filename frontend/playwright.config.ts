import { defineConfig } from '@playwright/test';
export default defineConfig({
 testDir:'e2e',workers:1,timeout:120000,expect:{timeout:30000},
 use:{baseURL:'http://127.0.0.1:4201',browserName:'chromium',trace:'retain-on-failure'},
 webServer:[
  {command:'uv run --all-extras uvicorn backend.main:app --host 127.0.0.1 --port 8001',cwd:'..',url:'http://127.0.0.1:8001/api/v1/health',timeout:120000,env:{OPENAI_API_KEY:''}},
  {command:'npx ng serve --host 127.0.0.1 --port 4201 --proxy-config proxy.e2e.conf.json',url:'http://127.0.0.1:4201',timeout:300000}
 ]
});
