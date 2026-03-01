import { redirect } from 'next/navigation';

export default function ShopPage() {
  redirect('/category?slug=all');
}
