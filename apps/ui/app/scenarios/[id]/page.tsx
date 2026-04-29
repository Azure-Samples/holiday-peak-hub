import { notFound } from 'next/navigation';
import { ScenarioDetailPage } from './ScenarioDetailPage';
import { isScenarioId } from '@/lib/demo/scenarios';

export default async function ScenarioPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;

  if (!isScenarioId(id)) {
    notFound();
  }

  return <ScenarioDetailPage scenarioId={id} />;
}