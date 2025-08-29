import { test, expect } from '@playwright/test';

test('chat interface responds with greeting', async ({ page }) => {
  await page.route('/api/user', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-user',
        display_name: 'TestUser',
        email: 'test@example.com'
      })
    });
  });

  await page.goto('/');
  
  await page.evaluate(() => {
    localStorage.setItem('spotify_token', 'mock-token');
  });
  
  await page.reload();
  
  await page.waitForSelector('[data-testid="chat-interface"]', { timeout: 10000 });
  
  await page.fill('[data-testid="chat-input"]', 'Hello');
  await page.click('[data-testid="send-button"]');
  
  await page.waitForSelector('[data-testid="chat-message"]:has-text("Hello TestUser")', { timeout: 5000 });
  
  const assistantMessage = page.locator('[data-testid="chat-message"]').filter({ hasText: 'Hello TestUser' });
  await expect(assistantMessage).toContainText('Hello TestUser');
});