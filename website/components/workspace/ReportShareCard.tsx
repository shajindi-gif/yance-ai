'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import type { Opportunity } from '@/lib/api';
import {
  SHARE_CARD_HEIGHT,
  SHARE_CARD_WIDTH,
  SHARE_DISCLAIMER,
  buildShareModel,
  drawShareCard,
  shareCopy,
} from '@/lib/share-card';
import styles from './ReportShareCard.module.css';

function fileStamp(now: Date) {
  return `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`;
}

export default function ReportShareCard({
  opportunities,
  companyName,
}: {
  opportunities: Opportunity[];
  companyName?: string | null;
}) {
  const [open, setOpen] = useState(false);
  const [showCompany, setShowCompany] = useState(false);
  const [status, setStatus] = useState('');
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const model = useMemo(
    () => buildShareModel(opportunities, { companyName, showCompany, now: new Date() }),
    [opportunities, companyName, showCompany],
  );

  useEffect(() => {
    if (!open || !canvasRef.current) return;
    const canvas = canvasRef.current;
    canvas.width = SHARE_CARD_WIDTH;
    canvas.height = SHARE_CARD_HEIGHT;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      setStatus('当前浏览器不支持图片生成，请复制文案分享。');
      return;
    }
    drawShareCard(ctx, model);
    setStatus('');
  }, [open, model]);

  function toBlob(): Promise<Blob> {
    const canvas = canvasRef.current;
    if (!canvas) return Promise.reject(new Error('图片尚未生成'));
    return new Promise((resolve, reject) =>
      canvas.toBlob(blob => (blob ? resolve(blob) : reject(new Error('图片导出失败，请重试'))), 'image/png'),
    );
  }

  async function download() {
    try {
      const blob = await toBlob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `衍策政策机会_${fileStamp(new Date())}.png`;
      anchor.click();
      URL.revokeObjectURL(url);
      setStatus('图片已生成，可发送到社交平台。');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '图片导出失败，请重试');
    }
  }

  async function share() {
    try {
      const blob = await toBlob();
      const file = new File([blob], `衍策政策机会_${fileStamp(new Date())}.png`, { type: 'image/png' });
      if (typeof navigator.share === 'function' && navigator.canShare?.({ files: [file] })) {
        await navigator.share({ files: [file], title: '衍策政策机会扫描', text: shareCopy(model) });
        setStatus('已打开系统分享。');
      } else {
        setStatus('当前浏览器不支持直接分享图片，请先下载 PNG 再分享。');
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return;
      setStatus(error instanceof Error ? error.message : '分享失败，请下载后手动分享');
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(shareCopy(model));
      setStatus('分享文案已复制。');
    } catch {
      setStatus('复制失败，请手动选择文案。');
    }
  }

  return (
    <div className={styles.wrap}>
      <Button
        type="button"
        variant="secondary"
        disabled={opportunities.length === 0}
        aria-expanded={open}
        onClick={() => setOpen(value => !value)}
      >
        {open ? '收起分享图' : '生成分享图'}
      </Button>
      {open && (
        <section className={styles.panel} aria-label="报告分享图">
          <div className={styles.preview}>
            <canvas ref={canvasRef} className={styles.canvas} role="img" aria-label={model.headline} />
          </div>
          <div className={styles.side}>
            <p>图片只含可优先核对的政策标题与统计，默认不显示企业名称。</p>
            <label className={styles.check}>
              <input type="checkbox" checked={showCompany} onChange={event => setShowCompany(event.target.checked)} />
              显示企业名称
            </label>
            <div className={styles.actions}>
              <Button type="button" onClick={download}>下载 PNG</Button>
              <Button type="button" variant="secondary" onClick={share}>系统分享</Button>
              <Button type="button" variant="secondary" onClick={copy}>复制分享文案</Button>
            </div>
            <p role="status" className={styles.status}>{status}</p>
            <p className={styles.note}>{SHARE_DISCLAIMER}</p>
          </div>
        </section>
      )}
    </div>
  );
}
