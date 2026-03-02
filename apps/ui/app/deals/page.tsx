import { redirect } from 'next/navigation';

export default function DealsPage() {
  redirect('/search?q=discount');
}
