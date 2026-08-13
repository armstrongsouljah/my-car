import { useCallback, useState } from 'react';
import { ActivityIndicator, Alert, Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { Stack, useFocusEffect, useLocalSearchParams, useRouter } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';
import { mediaUrl } from '@/lib/api';
import { useTheme } from '@/hooks/use-theme';
import type { Car } from '@/components/car-form';

const FUEL_LABELS: Record<string, string> = {
  petrol: 'Petrol',
  diesel: 'Diesel',
  hybrid: 'Hybrid',
  electric: 'Electric',
};

function DetailRow({ label, value }: { label: string; value: string }) {
  const theme = useTheme();
  return (
    <View style={styles.detailRow}>
      <ThemedText type="small" themeColor="textSecondary">
        {label}
      </ThemedText>
      <ThemedText style={value ? undefined : { color: theme.textSecondary }}>{value || '—'}</ThemedText>
    </View>
  );
}

export default function CarDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { apiCall } = useAuth();
  const theme = useTheme();
  const router = useRouter();

  const [car, setCar] = useState<Car | null>(null);
  const [error, setError] = useState('');
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(() => {
    apiCall(`/cars/${id}/`)
      .then((data) => setCar(data))
      .catch((err) => setError(err instanceof Error ? err.message : 'Something went wrong'));
  }, [apiCall, id]);

  // Refetch on focus so edits made on the edit screen show up on the way back.
  useFocusEffect(load);

  function confirmDelete() {
    Alert.alert('Delete car?', `This removes ${car?.make} ${car?.model} and its records. This can't be undone.`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: doDelete },
    ]);
  }

  async function doDelete() {
    setDeleting(true);
    try {
      await apiCall(`/cars/${id}/`, { method: 'DELETE' });
      router.back(); // Garage tab refetches on focus
    } catch (err) {
      setDeleting(false);
      Alert.alert('Couldn’t delete', err instanceof Error ? err.message : 'Something went wrong');
    }
  }

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
      <ScrollView contentContainerStyle={styles.scroll}>
        {car.photo_url ? (
          <Image source={{ uri: mediaUrl(car.photo_url) ?? undefined }} style={styles.photo} />
        ) : (
          <View style={[styles.photo, styles.photoPlaceholder, { backgroundColor: theme.backgroundElement }]}>
            <ThemedText type="title">🚗</ThemedText>
          </View>
        )}

        <Stack.Screen options={{ title: `${car.make} ${car.model}` }} />

        <ThemedText type="title" style={styles.title}>
          {car.make} {car.model} {car.year ? `(${car.year})` : ''}
        </ThemedText>

        <ThemedView type="backgroundElement" style={styles.card}>
          <DetailRow label="Plate no." value={car.registration_number} />
          <DetailRow label="Colour" value={car.color} />
          <DetailRow label="Fuel" value={FUEL_LABELS[car.fuel_type] ?? car.fuel_type} />
          <DetailRow label="Odometer" value={`${Number(car.current_odometer_km).toLocaleString()} km`} />
          <DetailRow label="VIN" value={car.vin} />
          <DetailRow label="Notes" value={car.notes} />
        </ThemedView>

        <View style={styles.actions}>
          <Pressable
            onPress={() => router.push(`/car/${id}/edit`)}
            accessibilityRole="button"
            style={[styles.actionButton, { backgroundColor: theme.brand }]}
          >
            <MaterialCommunityIcons name="pencil" color="#fff" size={18} />
            <ThemedText numberOfLines={1} style={styles.actionButtonText}>
              Edit
            </ThemedText>
          </Pressable>
          <Pressable
            onPress={confirmDelete}
            disabled={deleting}
            accessibilityRole="button"
            style={[styles.actionButton, styles.deleteButton, { borderColor: '#DC2626', opacity: deleting ? 0.6 : 1 }]}
          >
            {deleting ? (
              <ActivityIndicator color="#DC2626" />
            ) : (
              <>
                <MaterialCommunityIcons name="trash-can-outline" color="#DC2626" size={18} />
                <ThemedText numberOfLines={1} style={styles.deleteButtonText}>
                  Delete
                </ThemedText>
              </>
            )}
          </Pressable>
        </View>
      </ScrollView>
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
    gap: Spacing.three,
  },
  photo: {
    width: '100%',
    height: 200,
    borderRadius: Spacing.two,
  },
  photoPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  title: {
    fontSize: 24,
  },
  card: {
    borderRadius: Spacing.two,
    padding: Spacing.three,
    gap: Spacing.three,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  actions: {
    flexDirection: 'row',
    gap: Spacing.three,
  },
  actionButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.two,
    borderRadius: Spacing.two,
    paddingVertical: Spacing.three,
  },
  actionButtonText: {
    color: '#fff',
    fontWeight: '600',
  },
  deleteButton: {
    borderWidth: 1,
    backgroundColor: 'transparent',
  },
  deleteButtonText: {
    color: '#DC2626',
    fontWeight: '600',
  },
});
