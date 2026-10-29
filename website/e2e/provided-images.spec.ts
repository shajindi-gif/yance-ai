import {test,expect} from '@playwright/test';
const out='../docs/audit-evidence/provided-images-20261029';
test('provided imagery replaces generated scenes on desktop and mobile',async({page,baseURL})=>{
 expect(new URL(baseURL!).hostname).toMatch(/^(localhost|127\.0\.0\.1)$/);
 await page.route('**/*',r=>{const u=new URL(r.request().url());if(!['localhost','127.0.0.1'].includes(u.hostname)||u.pathname.startsWith('/api/'))return r.abort();return r.continue()});
 await page.goto('/');
 await expect(page.locator('#industry-scenes article')).toHaveCount(6);
 await expect(page.locator('img[src*="provided-20261029"]')).toHaveCount(7);
 await expect(page.locator('body')).not.toContainText('AI 生成');
 for(const old of ['manufacturing.webp','research.webp','business.webp'])await expect(page.locator(`img[src*="${old}"]`)).toHaveCount(0);
 for(const img of await page.locator('#industry-scenes img').all()){await img.scrollIntoViewIfNeeded();await expect.poll(()=>img.evaluate(e=>(e as HTMLImageElement).naturalWidth)).toBeGreaterThan(0)}
 await page.locator('#industry-scenes').screenshot({path:out+'/industries-desktop.png',style:'header { visibility:hidden !important; }'});
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:out+'/home-desktop.png'});
 for(const width of [390,768]){await page.setViewportSize({width,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await page.locator('#industry-scenes article').filter({hasText:'低空科技'}).screenshot({path:out+`/drone-${width}.png`});}
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:out+'/home-mobile.png'});
 await expect(page.locator('#for-business')).toContainText('各类有政策需求的企业');
 await expect(page.locator('#industry-scenes')).toContainText('图片由用户提供');
});
