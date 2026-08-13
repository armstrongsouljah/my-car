import { useCallback, useState } from 'react';
import { ActivityIndicator, Image, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useFocusEffect, useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { StatusChip } from '@/components/status-chip';
import { BottomTabInset, Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';
import { mediaUrl } from '@/lib/api';
import { formatAmount } from '@/lib/currency';
import { useTheme } from '@/hooks/use-theme';

type Car = {
  id: string;
  make: string;
  model: string;
  photo_url: string | null;
};

type Reminder = {
  id: string;
  car: string;
  title: string;
  message: string;
  status: 'overdue' | 'due_soon' | 'ok';
};

// The generic service/inspection nudges (not backed by a Reminder row --
// GET /services/reminders/, pre-filtered server-side to non-"ok" statuses).
type ServiceDigestEntry = {
  car_id: string;
  make: string;
  model: string;
  reminders: { kind: 'service' | 'inspection'; status: 'overdue' | 'due_soon' | 'ok'; message: string }[];
};

type UpcomingItem = {
  key: string;
  carId: string;
  title: string;
  subtitle: string;
  status: 'overdue' | 'due_soon' | 'ok';
};

type AnalyticsMonth = {
  total: number;
  change_percent_vs_previous_month: number | null;
};

// Mirrors frontend/app/dashboard/page.jsx's STATUS_PRIORITY/UPCOMING_COUNT --
// reminders sorted worst-first, capped so "See all" takes over past this.
const STATUS_PRIORITY: Record<string, number> = { overdue: 0, due_soon: 1, ok: 2 };
const UPCOMING_COUNT = 5;

export default function GarageScreen() {
  const { apiCall } = useAuth();
  const theme = useTheme();
  const router = useRouter();

  const [cars, setCars] = useState<Car[] | null>(null);
  const [carsError, setCarsError] = useState('');
  const [reminders, setReminders] = useState<Reminder[] | null>(null);
  const [remindersError, setRemindersError] = useState(false);
  const [servicesData, setServicesData] = useState<ServiceDigestEntry[] | null>(null);
  const [servicesError, setServicesError] = useState(false);
  const [month, setMonth] = useState<AnalyticsMonth | null>(null);
  const [currency, setCurrency] = useState<string | null>(null);
  const [analyticsError, setAnalyticsError] = useState(false);

  // Refetch whenever this tab regains focus (e.g. after adding a car),
  // not just on first mount -- same intent as the web pages' load-on-effect
  // pattern, adapted for a tab navigator where screens stay mounted.
  useFocusEffect(
    useCallback(() => {
      apiCall('/cars/')
        .then((data) => setCars(data.results || data))
        .catch((err) => setCarsError(err instanceof Error ? err.message : 'Something went wrong'));
      apiCall('/reminders/')
        .then((data) => setReminders(data.results || data))
        .catch(() => setRemindersError(true));
      apiCall('/services/reminders/')
        .then((data) => setServicesData(data))
        .catch(() => setServicesError(true));
      apiCall('/expenses/analytics/?months=1')
        .then((data) => {
          setMonth(data.months?.[0] ?? null);
          setCurrency(data.currency ?? null);
        })
        .catch(() => setAnalyticsError(true));
    }, [apiCall])
  );

  const carById = Object.fromEntries((cars ?? []).map((car) => [car.id, car]));

  // Normalized to a common shape so the render below doesn't need to branch
  // on which source an item came from -- a custom Reminder row (its own id,
  // opens the car it belongs to) vs. a computed service/inspection nudge
  // (no id of its own, same "open the car" target either way here).
  const customItems: UpcomingItem[] = (reminders ?? []).map((reminder) => ({
    key: reminder.id,
    carId: reminder.car,
    title: reminder.title,
    subtitle: `${carById[reminder.car] ? `${carById[reminder.car].make} ${carById[reminder.car].model} · ` : ''}${reminder.message}`,
    status: reminder.status,
  }));
  const serviceItems: UpcomingItem[] = (servicesData ?? []).flatMap((entry) =>
    entry.reminders.map((reminder) => ({
      key: `${entry.car_id}-${reminder.kind}`,
      carId: entry.car_id,
      title: reminder.kind === 'service' ? 'Service' : 'Inspection',
      subtitle: `${entry.make} ${entry.model} · ${reminder.message}`,
      status: reminder.status,
    }))
  );
  const upcoming = [...customItems, ...serviceItems]
    .sort((a, b) => (STATUS_PRIORITY[a.status] ?? 99) - (STATUS_PRIORITY[b.status] ?? 99))
    .slice(0, UPCOMING_COUNT);

  return (
    <ThemedView style={styles.container}>
      <SafeAreaView style={styles.container} edges={['top']}>
        <ThemedText type="title" style={styles.header}>
          Your Garage
        </ThemedText>

        <ScrollView contentContainerStyle={styles.scroll}>
          {carsError ? <ThemedText style={styles.error}>{carsError}</ThemedText> : null}

          {cars === null && !carsError && (
            <View style={styles.loading}>
              <ActivityIndicator color={theme.brand} />
            </View>
          )}

          {cars?.length === 0 && (
            <ThemedView type="backgroundElement" style={styles.emptyCard}>
              <ThemedText style={styles.emptyEmoji}>🅿️</ThemedText>
              <ThemedText type="smallBold" style={styles.emptyTitle}>
                No cars yet
              </ThemedText>
              <ThemedText type="small" themeColor="textSecondary" style={styles.emptyBody}>
                Add your first car to start tracking services and expenses.
              </ThemedText>
            </ThemedView>
          )}

          {cars && cars.length > 0 && (
            <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.pillRow}>
              {cars.map((car) => (
                <Pressable key={car.id} onPress={() => router.push(`/car/${car.id}`)} accessibilityRole="button" style={styles.pillItem}>
                  {car.photo_url ? (
                    <Image source={{ uri: mediaUrl(car.photo_url) ?? undefined }} style={styles.pillPhoto} />
                  ) : (
                    <View style={[styles.pillPhoto, styles.pillPhotoPlaceholder, { backgroundColor: theme.backgroundSelected }]}>
                      <ThemedText>🚗</ThemedText>
                    </View>
                  )}
                  <ThemedText type="small" numberOfLines={1} style={styles.pillLabel}>
                    {car.model}
                  </ThemedText>
                </Pressable>
              ))}
            </ScrollView>
          )}

          {cars && cars.length > 0 && (
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <ThemedText type="smallBold">Upcoming</ThemedText>
                <Pressable onPress={() => router.push('/(tabs)/reminders')} accessibilityRole="button">
                  <ThemedText type="small" style={{ color: theme.brand }}>
                    See all
                  </ThemedText>
                </Pressable>
              </View>

              {(reminders === null && servicesData === null) && !remindersError && !servicesError ? (
                <View style={styles.loading}>
                  <ActivityIndicator color={theme.brand} />
                </View>
              ) : remindersError && servicesError ? (
                <ThemedView type="backgroundElement" style={styles.messageCard}>
                  <ThemedText type="small" themeColor="textSecondary">
                    Couldn’t load reminders right now.
                  </ThemedText>
                </ThemedView>
              ) : upcoming.length === 0 ? (
                <ThemedView type="backgroundElement" style={styles.messageCard}>
                  <ThemedText type="small" themeColor="textSecondary">
                    No reminders yet — add one to stay on top of maintenance.
                  </ThemedText>
                </ThemedView>
              ) : (
                <View style={styles.reminderList}>
                  {upcoming.map((item) => (
                    <Pressable key={item.key} onPress={() => router.push(`/car/${item.carId}`)} accessibilityRole="button">
                      <ThemedView type="backgroundElement" style={styles.reminderCard}>
                        <View style={styles.reminderBody}>
                          <ThemedText type="smallBold" numberOfLines={1}>
                            {item.title}
                          </ThemedText>
                          <ThemedText type="small" themeColor="textSecondary" numberOfLines={1}>
                            {item.subtitle}
                          </ThemedText>
                        </View>
                        <StatusChip status={item.status} />
                      </ThemedView>
                    </Pressable>
                  ))}
                </View>
              )}
            </View>
          )}

          {cars && cars.length > 0 && (
            <View style={styles.section}>
              <View style={styles.sectionHeader}>
                <ThemedText type="smallBold">Spending</ThemedText>
                <Pressable onPress={() => router.push('/(tabs)/expenses')} accessibilityRole="button">
                  <ThemedText type="small" style={{ color: theme.brand }}>
                    See details
                  </ThemedText>
                </Pressable>
              </View>

              {month === null && !analyticsError ? (
                <View style={styles.loading}>
                  <ActivityIndicator color={theme.brand} />
                </View>
              ) : analyticsError ? (
                <ThemedView type="backgroundElement" style={styles.messageCard}>
                  <ThemedText type="small" themeColor="textSecondary">
                    Couldn’t load spending right now.
                  </ThemedText>
                </ThemedView>
              ) : (
                <ThemedView type="backgroundElement" style={styles.spendingCard}>
                  <View style={styles.spendingRow}>
                    <ThemedText type="smallBold">This month</ThemedText>
                    <ThemedText type="smallBold" style={styles.spendingTotal}>
                      {formatAmount(month!.total, currency)}
                    </ThemedText>
                  </View>
                  {month!.change_percent_vs_previous_month !== null && month!.change_percent_vs_previous_month !== undefined && (
                    <ThemedText
                      type="small"
                      style={{ color: month!.change_percent_vs_previous_month > 0 ? '#f87171' : '#4ade80' }}
                    >
                      {month!.change_percent_vs_previous_month > 0 ? '▲' : '▼'} {Math.abs(month!.change_percent_vs_previous_month)}%
                      vs last month
                    </ThemedText>
                  )}
                </ThemedView>
              )}
            </View>
          )}
        </ScrollView>

        <Pressable
          onPress={() => router.push('/add-car')}
          accessibilityRole="button"
          accessibilityLabel="Add car"
          style={[styles.fab, { backgroundColor: theme.brandEmphasis, bottom: BottomTabInset + Spacing.three }]}
        >
          <MaterialCommunityIcons name="plus" color="#fff" size={18} />
          <ThemedText numberOfLines={1} style={styles.fabText}>
            Add car
          </ThemedText>
        </Pressable>
      </SafeAreaView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    fontSize: 28,
    paddingHorizontal: Spacing.three,
    paddingTop: Spacing.two,
    paddingBottom: Spacing.three,
  },
  scroll: {
    paddingHorizontal: Spacing.three,
    paddingBottom: Spacing.six,
  },
  error: {
    color: '#DC2626',
    marginBottom: Spacing.three,
  },
  loading: {
    paddingVertical: Spacing.four,
    alignItems: 'center',
  },
  emptyCard: {
    padding: Spacing.four,
    borderRadius: Spacing.three,
    alignItems: 'center',
  },
  emptyEmoji: {
    fontSize: 28,
  },
  emptyTitle: {
    marginTop: Spacing.two,
  },
  emptyBody: {
    marginTop: Spacing.one,
    textAlign: 'center',
  },
  pillRow: {
    gap: Spacing.three,
    paddingBottom: Spacing.two,
  },
  pillItem: {
    width: 64,
    alignItems: 'center',
    gap: Spacing.one,
  },
  pillPhoto: {
    width: 56,
    height: 56,
    borderRadius: 28,
  },
  pillPhotoPlaceholder: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  pillLabel: {
    textAlign: 'center',
  },
  section: {
    marginTop: Spacing.four,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: Spacing.two,
  },
  messageCard: {
    padding: Spacing.three,
    borderRadius: Spacing.two,
    alignItems: 'center',
  },
  reminderList: {
    gap: Spacing.two,
  },
  reminderCard: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.three,
    padding: Spacing.three,
    borderRadius: Spacing.two,
  },
  reminderBody: {
    flex: 1,
    gap: 2,
  },
  spendingCard: {
    padding: Spacing.three,
    borderRadius: Spacing.two,
    gap: Spacing.one,
  },
  spendingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  spendingTotal: {
    fontSize: 20,
  },
  fab: {
    position: 'absolute',
    right: Spacing.three,
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.two,
    paddingHorizontal: Spacing.four,
    paddingVertical: Spacing.three,
    borderRadius: 999,
    shadowColor: '#000',
    shadowOpacity: 0.3,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 6,
  },
  fabText: {
    color: '#fff',
    fontWeight: '600',
  },
});
