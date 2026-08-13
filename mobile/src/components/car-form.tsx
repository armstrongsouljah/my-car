import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, FlatList, Image, Modal, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { Spacing } from '@/constants/theme';
import { useAuth } from '@/lib/auth-context';
import { mediaUrl } from '@/lib/api';
import { useTheme } from '@/hooks/use-theme';

const CLOUDINARY_CLOUD_NAME = process.env.EXPO_PUBLIC_CLOUDINARY_CLOUD_NAME;
const CLOUDINARY_UPLOAD_PRESET = process.env.EXPO_PUBLIC_CLOUDINARY_UPLOAD_PRESET;

// Uploads straight from the device to Cloudinary (unsigned preset) -- the
// API never sees the file, only the resulting secure_url. Mirrors frontend/
// components/CarForm.jsx's uploadToCloudinary, adapted for RN's FormData
// (a {uri, type, name} object stands in for the browser's File/Blob).
async function uploadToCloudinary(asset: ImagePicker.ImagePickerAsset) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  const body = new FormData();
  body.append('file', {
    uri: asset.uri,
    type: asset.mimeType || 'image/jpeg',
    name: asset.fileName || 'photo.jpg',
  } as unknown as Blob);
  body.append('upload_preset', CLOUDINARY_UPLOAD_PRESET ?? '');

  let res: Response;
  try {
    res = await fetch(`https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload`, {
      method: 'POST',
      body,
      signal: controller.signal,
    });
  } catch (err) {
    throw new Error(err instanceof Error && err.name === 'AbortError' ? 'Photo upload timed out. Please try again.' : 'Photo upload failed. Please try again.');
  } finally {
    clearTimeout(timeout);
  }
  if (!res.ok) throw new Error('Photo upload failed. Please try again.');
  const data = await res.json();
  return data.secure_url as string;
}

const OTHER = '__other__';

type Catalog = { brands: { name: string; models: string[] }[]; years: number[] };

export type Car = {
  id: string;
  make: string;
  model: string;
  year: number | null;
  registration_number: string;
  vin: string;
  color: string;
  fuel_type: string;
  photo_url: string | null;
  current_odometer_km: number;
  notes: string;
};

const FUEL_TYPES: { value: string; label: string }[] = [
  { value: 'petrol', label: 'Petrol' },
  { value: 'diesel', label: 'Diesel' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'electric', label: 'Electric' },
];

// Modal picker shared by the brand/model/year fields below -- mirrors the
// role of frontend/components/CarForm.jsx's native <select>s, since RN has
// no equivalent element.
function PickerField({
  label,
  placeholder,
  value,
  options,
  onSelect,
  disabled,
}: {
  label: string;
  placeholder: string;
  value: string;
  options: string[];
  onSelect: (value: string) => void;
  disabled?: boolean;
}) {
  const theme = useTheme();
  const [open, setOpen] = useState(false);

  return (
    <>
      <Pressable
        onPress={() => setOpen(true)}
        disabled={disabled}
        accessibilityRole="button"
        style={[styles.input, styles.pickerField, { borderColor: theme.backgroundSelected, opacity: disabled ? 0.5 : 1 }]}
      >
        <ThemedText numberOfLines={1} style={value ? undefined : { color: theme.textSecondary }}>
          {value || placeholder}
        </ThemedText>
        <MaterialCommunityIcons name="chevron-down" size={20} color={theme.textSecondary} />
      </Pressable>

      <Modal visible={open} animationType="slide" transparent onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.modalBackdrop} onPress={() => setOpen(false)} />
        <ThemedView type="background" style={styles.modalSheet}>
          <ThemedText type="smallBold" style={styles.modalTitle}>
            {label}
          </ThemedText>
          <FlatList
            data={options}
            keyExtractor={(item) => item}
            style={styles.modalList}
            renderItem={({ item }) => (
              <Pressable
                onPress={() => {
                  onSelect(item);
                  setOpen(false);
                }}
                style={[styles.modalOption, { borderBottomColor: theme.backgroundSelected }]}
              >
                <ThemedText>{item === OTHER ? 'Other…' : item}</ThemedText>
              </Pressable>
            )}
          />
        </ThemedView>
      </Modal>
    </>
  );
}

export function CarForm({ car = null, onSaved }: { car?: Car | null; onSaved: (car: Car) => void }) {
  const { apiCall } = useAuth();
  const theme = useTheme();
  const isEdit = !!car;

  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [brandChoice, setBrandChoice] = useState('');
  const [make, setMake] = useState(car?.make ?? '');
  const [modelChoice, setModelChoice] = useState('');
  const [model, setModel] = useState(car?.model ?? '');
  const [year, setYear] = useState(car?.year ? String(car.year) : '');
  const [registrationNumber, setRegistrationNumber] = useState(car?.registration_number ?? '');
  const [color, setColor] = useState(car?.color ?? '');
  const [fuelType, setFuelType] = useState(car?.fuel_type ?? 'petrol');
  const [odometerKm, setOdometerKm] = useState(car?.current_odometer_km != null ? String(car.current_odometer_km) : '');
  const [vin, setVin] = useState(car?.vin ?? '');
  const [notes, setNotes] = useState(car?.notes ?? '');
  const [photo, setPhoto] = useState<ImagePicker.ImagePickerAsset | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(mediaUrl(car?.photo_url));
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    apiCall('/cars/catalog/')
      .then((data) => {
        setCatalog(data);
        if (car) {
          const brands: string[] = data.brands.map((b: { name: string }) => b.name);
          const knownBrand = brands.includes(car.make);
          const models: string[] = knownBrand ? data.brands.find((b: { name: string }) => b.name === car.make).models : [];
          setBrandChoice(knownBrand ? car.make : OTHER);
          setModelChoice(knownBrand && models.includes(car.model) ? car.model : OTHER);
        }
      })
      .catch(() => setCatalog({ brands: [], years: [] })); // falls back to free-text below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const brandOptions = useMemo(() => [...(catalog?.brands.map((b) => b.name) ?? []), OTHER], [catalog]);
  const modelOptions = useMemo(() => {
    if (!catalog || !brandChoice || brandChoice === OTHER) return [];
    return [...(catalog.brands.find((b) => b.name === brandChoice)?.models ?? []), OTHER];
  }, [catalog, brandChoice]);
  const yearOptions = useMemo(() => catalog?.years.map(String) ?? [], [catalog]);

  function pickBrand(value: string) {
    setBrandChoice(value);
    setMake(value === OTHER ? '' : value);
    setModelChoice('');
    setModel('');
  }

  function pickModel(value: string) {
    setModelChoice(value);
    setModel(value === OTHER ? '' : value);
  }

  async function pickPhoto() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError('Photo library access is needed to add a car photo.');
      return;
    }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      quality: 0.8,
      allowsEditing: true,
      aspect: [4, 3],
    });
    if (result.canceled || !result.assets[0]) return;
    setPhoto(result.assets[0]);
    setPhotoPreview(result.assets[0].uri);
  }

  async function submit() {
    setError('');
    setLoading(true);
    try {
      const fields: Record<string, unknown> = {
        make: make.trim(),
        model: model.trim(),
        year: year ? Number(year) : null,
        registration_number: registrationNumber,
        color,
        fuel_type: fuelType,
        current_odometer_km: odometerKm ? Number(odometerKm) : 0,
        vin,
        notes,
      };

      if (photo) {
        fields.photo_url = await uploadToCloudinary(photo);
      }

      const path = isEdit ? `/cars/${car.id}/` : '/cars/';
      const method = isEdit ? 'PATCH' : 'POST';
      const saved = await apiCall(path, { method, body: fields });
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = !!make.trim() && !!model.trim();

  return (
    <View style={styles.form}>
      {error ? (
        <ThemedText type="small" style={styles.error}>
          {error}
        </ThemedText>
      ) : null}

      <Pressable onPress={pickPhoto} accessibilityRole="button">
        {photoPreview ? (
          <Image source={{ uri: photoPreview }} style={styles.photo} />
        ) : (
          <View style={[styles.photo, styles.photoPlaceholder, { borderColor: theme.backgroundSelected }]}>
            <ThemedText type="title" style={styles.photoPlaceholderEmoji}>
              📷
            </ThemedText>
            <ThemedText type="small" themeColor="textSecondary">
              Add a photo of your car
            </ThemedText>
          </View>
        )}
      </Pressable>

      <PickerField label="Brand" placeholder="Select a brand…" value={brandChoice} options={brandOptions} onSelect={pickBrand} />
      {brandChoice === OTHER && (
        <TextInput
          value={make}
          onChangeText={setMake}
          placeholder="Type the brand"
          placeholderTextColor={theme.textSecondary}
          style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
        />
      )}

      {brandChoice && brandChoice !== OTHER ? (
        <>
          <PickerField label="Model" placeholder="Select a model…" value={modelChoice} options={modelOptions} onSelect={pickModel} />
          {modelChoice === OTHER && (
            <TextInput
              value={model}
              onChangeText={setModel}
              placeholder="Type the model"
              placeholderTextColor={theme.textSecondary}
              style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
            />
          )}
        </>
      ) : (
        <TextInput
          value={model}
          onChangeText={setModel}
          placeholder={brandChoice === OTHER ? 'Type the model' : 'Pick a brand first'}
          placeholderTextColor={theme.textSecondary}
          editable={brandChoice === OTHER}
          style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected, opacity: brandChoice === OTHER ? 1 : 0.5 }]}
        />
      )}

      <PickerField label="Year" placeholder="Year" value={year} options={yearOptions} onSelect={setYear} />
      <TextInput
        value={registrationNumber}
        onChangeText={setRegistrationNumber}
        placeholder="Plate no. (optional)"
        placeholderTextColor={theme.textSecondary}
        autoCapitalize="characters"
        style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
      />
      <TextInput
        value={color}
        onChangeText={setColor}
        placeholder="Colour"
        placeholderTextColor={theme.textSecondary}
        style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
      />
      <TextInput
        value={odometerKm}
        onChangeText={setOdometerKm}
        placeholder="Odometer (km)"
        placeholderTextColor={theme.textSecondary}
        keyboardType="number-pad"
        style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
      />

      <ThemedText type="small" themeColor="textSecondary" style={styles.label}>
        Fuel
      </ThemedText>
      <View style={styles.pillRow}>
        {FUEL_TYPES.map((fuel) => {
          const selected = fuel.value === fuelType;
          return (
            <Pressable
              key={fuel.value}
              onPress={() => setFuelType(fuel.value)}
              accessibilityRole="button"
              style={[
                styles.pill,
                { backgroundColor: selected ? theme.brand : theme.backgroundElement, borderColor: selected ? theme.brand : theme.backgroundSelected },
              ]}
            >
              <ThemedText numberOfLines={1} style={selected ? styles.pillTextSelected : undefined}>
                {fuel.label}
              </ThemedText>
            </Pressable>
          );
        })}
      </View>

      <TextInput
        value={vin}
        onChangeText={setVin}
        placeholder="VIN (optional)"
        placeholderTextColor={theme.textSecondary}
        autoCapitalize="characters"
        style={[styles.input, { color: theme.text, borderColor: theme.backgroundSelected }]}
      />
      <TextInput
        value={notes}
        onChangeText={setNotes}
        placeholder="Notes (optional)"
        placeholderTextColor={theme.textSecondary}
        multiline
        numberOfLines={3}
        style={[styles.input, styles.notesInput, { color: theme.text, borderColor: theme.backgroundSelected }]}
      />

      <Pressable
        onPress={submit}
        disabled={loading || !canSubmit}
        accessibilityRole="button"
        style={[styles.button, { backgroundColor: theme.brand, opacity: loading || !canSubmit ? 0.6 : 1 }]}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <ThemedText numberOfLines={1} style={styles.buttonText}>
            {isEdit ? 'Save changes' : 'Add car'}
          </ThemedText>
        )}
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  form: {
    gap: Spacing.two,
  },
  error: {
    color: '#DC2626',
    textAlign: 'center',
  },
  photo: {
    width: '100%',
    height: 160,
    borderRadius: Spacing.two,
  },
  photoPlaceholder: {
    borderWidth: 1,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.one,
  },
  photoPlaceholderEmoji: {
    fontSize: 28,
  },
  input: {
    borderWidth: 1,
    borderRadius: Spacing.two,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
    fontSize: 15,
  },
  pickerField: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  notesInput: {
    minHeight: 80,
    textAlignVertical: 'top',
  },
  label: {
    marginBottom: -Spacing.two,
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.two,
  },
  pill: {
    borderWidth: 1,
    borderRadius: Spacing.four,
    paddingHorizontal: Spacing.three,
    paddingVertical: Spacing.two,
  },
  pillTextSelected: {
    color: '#fff',
    fontWeight: '600',
  },
  button: {
    borderRadius: Spacing.two,
    paddingVertical: Spacing.three,
    alignItems: 'center',
    marginTop: Spacing.two,
  },
  buttonText: {
    color: '#fff',
    fontWeight: '600',
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
  },
  modalSheet: {
    maxHeight: '70%',
    borderTopLeftRadius: Spacing.three,
    borderTopRightRadius: Spacing.three,
    padding: Spacing.three,
  },
  modalTitle: {
    marginBottom: Spacing.two,
  },
  modalList: {
    flexGrow: 0,
  },
  modalOption: {
    paddingVertical: Spacing.three,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
});
