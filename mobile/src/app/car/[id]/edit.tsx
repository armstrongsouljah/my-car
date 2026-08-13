import { useCallback, useState } from 'react';
import { ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView, StyleSheet } from 'react-native';
import { useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';

import { CarForm, type Car } from '@/components/car-form';
import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';
import { useTheme } from '@/hooks/use-theme';

export default function EditCarScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { apiCall } = useAuth();
  const theme = useTheme();
  const router = useRouter();

  const [car, setCar] = useState<Car | null>(null);
  const [error, setError] = useState('');

  // Only load once -- CarForm owns its own fields after that; refetching on
  // every focus (like the detail/garage screens) would clobber in-progress edits.
  useFocusEffect(
    useCallback(() => {
      if (car) return;
      apiCall(`/cars/${id}/`)
        .then((data) => setCar(data))
        .catch((err) => setError(err instanceof Error ? err.message : 'Something went wrong'));
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [id])
  );

  if (error) {
    return (
      <ThemedView style={styles.container}>
        <ThemedText style={styles.error}>{error}</ThemedText>
      </ThemedView>
    );
  }

  if (!car) {
    return (
      <ThemedView style={[styles.container, styles.loading]}>
        <ActivityIndicator color={theme.brand} />
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <KeyboardAvoidingView style={styles.container} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <CarForm car={car} onSaved={() => router.back()} />
        </ScrollView>
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loading: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  error: {
    color: '#DC2626',
    textAlign: 'center',
    padding: Spacing.three,
  },
  scroll: {
    padding: Spacing.three,
  },
});
