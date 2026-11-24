'use client';
import { useEffect, useState } from 'react';
import QRCode from 'qrcode';

export default function PaymentQr({ value }: { value: string }) {
  const [image, setImage] = useState('');
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    setImage(''); setFailed(false);
    QRCode.toDataURL(value, { width: 240, margin: 2, errorCorrectionLevel: 'M' })
      .then(url => { if (active) setImage(url); })
      .catch(() => { if (active) setFailed(true); });
    return () => { active = false; };
  }, [value]);
  if (failed) return <p role="alert">二维码生成失败，请关闭后从已有订单重试。</p>;
  if (!image) return <p role="status">正在生成支付二维码…</p>;
  return <img src={image} alt="微信支付的二维码" width={240} height={240} />;
}
