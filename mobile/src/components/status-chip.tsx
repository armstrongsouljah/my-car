import { StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/themed-text';

// Mirrors frontend/components/StatusChip.jsx's palette/labels.
const STYLES: Record<string, { bg: string; text: string }> = {
  overdue: { bg: 'rgba(239,68,68,0.15)', text: '#f87171' },
  due_soon: { bg: 'rgba(245,158,11,0.15)', text: '#fbbf24' },
  ok: { bg: 'rgba(34,197,94,0.15)', text: '#4ade80' },
};

const LABELS: Record<string, string> = {
  overdue: 'Overdue',
  due_soon: 'Due soon',
  ok: 'OK',
};

export function StatusChip({ status }: { status: string }) {
  const palette = STYLES[status] ?? STYLES.ok;
  return (
    <View style={[styles.chip, { backgroundColor: palette.bg }]}>
      <ThemedText type="small" style={[styles.text, { color: palette.text }]}>
        {LABELS[status] ?? status}
      </ThemedText>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  text: {
    fontWeight: '600',
  },
});
