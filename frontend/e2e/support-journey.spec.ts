// A customer opens a request in the portal; an agent answers it from the console; the customer sees the answer.
import { expect, test } from '@playwright/test';

test('portal request → console reply → customer sees it', async ({ browser }) => {
  const subject = `Invoices page is blank ${Date.now()}`;

  const customer = await (await browser.newContext()).newPage();
  await customer.goto('/portal/acme/sign-in');
  await customer.getByLabel('Work email').fill('customer@globex.demo');
  await customer.getByLabel('Password').fill('Demo@1234');
  await customer.getByRole('button', { name: 'Sign in' }).click();
  await customer.getByRole('link', { name: 'New request' }).first().click();
  await customer.getByLabel('Subject').fill(subject);
  await customer.getByLabel('Describe the problem').fill('Since this morning the invoices page shows nothing.');
  await customer.getByLabel('How urgent is it?').selectOption('high');
  await customer.getByRole('button', { name: 'Submit request' }).click();
  await expect(customer.getByRole('heading', { name: subject })).toBeVisible();

  const agent = await (await browser.newContext()).newPage();
  await agent.goto('/login');
  await agent.getByLabel('Work email').fill('agent@acme.demo');
  await agent.getByLabel('Password').fill('Demo@1234');
  await agent.getByRole('button', { name: 'Sign in' }).click();
  await agent.getByRole('link', { name: 'All tickets' }).click();
  await agent.getByLabel('Search').fill(subject.split(' ').slice(0, 3).join(' '));
  await agent.getByRole('link', { name: new RegExp(subject) }).click();
  await expect(agent.getByRole('heading', { name: subject })).toBeVisible();
  await expect(agent.getByText('Since this morning the invoices page shows nothing.')).toBeVisible();

  await agent.getByPlaceholder('Write a reply to the customer…').fill('Thanks Dana, we are on it. A fix ships today.');
  await agent.getByRole('button', { name: 'Send', exact: true }).click();
  await expect(agent.getByRole('complementary', { name: 'Ticket properties' }).getByLabel('Status')).toHaveValue('pending_customer');

  await customer.reload();
  await expect(customer.getByText('Thanks Dana, we are on it. A fix ships today.')).toBeVisible();
  await expect(customer.getByText('Waiting on customer')).toBeVisible();
});

test('a customer cannot use the console', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Work email').fill('customer@globex.demo');
  await page.getByLabel('Password').fill('Demo@1234');
  await page.getByRole('button', { name: 'Sign in' }).click();
  await expect(page.getByRole('alert')).toContainText('customer account');
});
