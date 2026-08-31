import { redirect } from 'next/navigation';

export default function DemoPage() {
  redirect('/login?register=1');
}
