import {expect,test} from '@playwright/test';

// e58a7c4 application detail and comment contract, with no V2 capability flag.
test('legacy application preserves general comments and hides unsupported V2 writes',async ({page}) => {
  const comments:Array<{id:string;body:string;created_at:string}>=[];
  const app={id:'legacy-contract',company_id:'synthetic',company_name:'合成旧版企业',title:'合成兼容项目',status:'draft',progress:0,review_status:'pending',readiness:{requirement_ready:0,verified_evidence:0,can_submit_for_review:false,blockers:['合成缺口']},requirements:[],documents:[],generated:[],tasks:[],evidence:[],activities:[],comments};
  const writes:Array<Record<string,unknown>>=[];
  await page.addInitScript(() => localStorage.setItem('yance_token','synthetic-contract-only'));
  await page.route('**/*',route => {
    const url=new URL(route.request().url());
    if(!['127.0.0.1','localhost'].includes(url.hostname))return route.abort();
    if(!url.pathname.startsWith('/api/'))return route.continue();
    if(route.request().method()==='POST') {
      expect(url.pathname).toBe('/api/v1/applications/legacy-contract/comments');
      const payload=route.request().postDataJSON();writes.push(payload);
      const comment={id:'comment-legacy',body:payload.body,created_at:'2026-10-25T00:00:00Z'};
      comments.push(comment);return route.fulfill({json:comment,status:201});
    }
    return route.fulfill({json:url.pathname.endsWith('/auth/config')?{email_login_enabled:false}:url.pathname.endsWith('/auth/me')?{role:'owner'}:url.pathname.includes('/applications/')?app:[]});
  });
  await page.goto('/applications/legacy-contract');
  await expect(page.getByText(/当前为兼容工作区/)).toBeVisible();
  await expect(page.getByRole('tab',{name:'项目概览',exact:true})).toHaveAttribute('aria-selected','true');
  await expect(page.getByRole('tab',{name:'资格矩阵',exact:true})).toHaveCount(0);
  await page.getByRole('tab',{name:'动态',exact:true}).click();
  await expect(page.getByRole('combobox',{name:'评论关联版本'})).toHaveCount(0);
  await expect(page.getByRole('textbox',{name:'建议替换摘要（可选）'})).toHaveCount(0);
  await page.getByRole('textbox',{name:'添加协作评论'}).fill('旧版项目评论');
  await page.getByRole('button',{name:'发送',exact:true}).click();
  await expect(page.getByText('旧版项目评论',{exact:true})).toBeVisible();
  expect(writes).toEqual([{body:'旧版项目评论'}]);
  await page.getByRole('tab',{name:/工作稿/}).click();
  await expect(page.getByRole('button',{name:'重新生成',exact:true})).toBeEnabled();
});
