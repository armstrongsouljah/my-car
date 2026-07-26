"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { trackSignal } from "@/lib/telemetry";

const OTHER = "__other__";
const FUEL_TYPES = ["petrol", "diesel", "hybrid", "electric"];

const CLOUDINARY_CLOUD_NAME = process.env.NEXT_PUBLIC_CLOUDINARY_CLOUD_NAME;
const CLOUDINARY_UPLOAD_PRESET = process.env.NEXT_PUBLIC_CLOUDINARY_UPLOAD_PRESET;

// Uploads straight from the browser to Cloudinary (unsigned preset) — the
// API never sees the file, only the resulting secure_url. Bounded by a
// timeout so a hung request can't leave the form stuck in "Saving…" forever.
async function uploadToCloudinary(file) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30000);

  const body = new FormData();
  body.append("file", file);
  body.append("upload_preset", CLOUDINARY_UPLOAD_PRESET);

  let res;
  try {
    res = await fetch(`https://api.cloudinary.com/v1_1/${CLOUDINARY_CLOUD_NAME}/image/upload`, {
      method: "POST",
      body,
      signal: controller.signal,
    });
  } catch (err) {
    throw new Error(err.name === "AbortError" ? "Photo upload timed out. Please try again." : "Photo upload failed. Please try again.");
  } finally {
    clearTimeout(timeout);
  }
  if (!res.ok) throw new Error("Photo upload failed. Please try again.");
  const data = await res.json();
  return data.secure_url;
}

/**
 * Shared create/edit car form. Brand → model pickers are driven by the API's
 * bundled catalog with a free-text "Other" fallback; years are selectable
 * from the catalog range (min 1980). Photos upload directly to Cloudinary
 * from the browser; only the resulting URL is sent to the API.
 */
export default function CarForm({ car = null, onSaved }) {
  const isEdit = !!car;
  const [catalog, setCatalog] = useState(null);
  const [form, setForm] = useState({
    brandChoice: "", make: "", modelChoice: "", model: "",
    year: car?.year ? String(car.year) : "",
    registration_number: car?.registration_number || "",
    vin: car?.vin || "",
    color: car?.color || "",
    fuel_type: car?.fuel_type || "petrol",
    current_odometer_km: car?.current_odometer_km ?? "",
    notes: car?.notes || "",
  });
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(car?.photo_url || null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api("/cars/catalog/")
      .then((data) => {
        setCatalog(data);
        if (car) {
          const brands = data.brands.map((b) => b.name);
          const knownBrand = brands.includes(car.make);
          const models = knownBrand ? data.brands.find((b) => b.name === car.make).models : [];
          setForm((prev) => ({
            ...prev,
            brandChoice: knownBrand ? car.make : OTHER,
            make: car.make,
            modelChoice: knownBrand && models.includes(car.model) ? car.model : OTHER,
            model: car.model,
          }));
        }
      })
      .catch(() => setCatalog({ brands: [], years: [], min_year: 1980 }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // Revoke the previous blob: URL whenever the preview changes (a new
    // photo is picked) and on unmount, so object URLs don't leak. The
    // initial preview sourced from car.photo_url is a normal http(s) URL
    // and is left alone.
    return () => {
      if (photoPreview?.startsWith("blob:")) URL.revokeObjectURL(photoPreview);
    };
  }, [photoPreview]);

  const models = useMemo(() => {
    if (!catalog || !form.brandChoice || form.brandChoice === OTHER) return [];
    return catalog.brands.find((b) => b.name === form.brandChoice)?.models || [];
  }, [catalog, form.brandChoice]);

  const update = (key) => (event) => setForm({ ...form, [key]: event.target.value });

  function pickBrand(event) {
    const value = event.target.value;
    setForm({
      ...form,
      brandChoice: value,
      make: value === OTHER ? "" : value,
      modelChoice: "",
      model: "",
    });
  }

  function pickModel(event) {
    const value = event.target.value;
    setForm({ ...form, modelChoice: value, model: value === OTHER ? "" : value });
  }

  function pickPhoto(event) {
    const file = event.target.files?.[0] || null;
    setPhoto(file);
    setPhotoPreview(file ? URL.createObjectURL(file) : car?.photo_url || null);
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!form.make.trim() || !form.model.trim()) {
      setError("Pick a brand and model (or choose Other and type them in).");
      return;
    }

    setLoading(true);
    try {
      const year = form.year ? Number(form.year) : null;
      const fields = {
        make: form.make.trim(),
        model: form.model.trim(),
        registration_number: form.registration_number,
        vin: form.vin,
        color: form.color,
        fuel_type: form.fuel_type,
        current_odometer_km: form.current_odometer_km || 0,
        notes: form.notes,
      };

      if (photo) {
        fields.photo_url = await uploadToCloudinary(photo);
      }

      const path = isEdit ? `/cars/${car.id}/` : "/cars/";
      const method = isEdit ? "PATCH" : "POST";
      const saved = await api(path, { method, body: { ...fields, year } });
      trackSignal(isEdit ? "car_updated" : "car_added");
      onSaved(saved);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700 dark:bg-red-500/10 dark:text-red-400">{error}</p>}

      {/* Photo */}
      <div>
        <label className="label">Photo</label>
        <label className="block cursor-pointer">
          {photoPreview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={photoPreview} alt="Car" className="h-44 w-full rounded-2xl border border-gray-200 object-cover dark:border-gray-800" />
          ) : (
            <div className="flex h-44 w-full flex-col items-center justify-center gap-1 rounded-2xl border-2 border-dashed border-gray-300 bg-gray-50 text-gray-400 dark:border-gray-700 dark:bg-gray-800/60 dark:text-gray-500">
              <span className="text-3xl">📷</span>
              <span className="text-sm font-medium">Add a photo of your car</span>
            </div>
          )}
          <input type="file" accept="image/*" className="hidden" onChange={pickPhoto} />
        </label>
      </div>

      {/* Brand / model */}
      <div>
        <label className="label">Brand *</label>
        <select className="input" required value={form.brandChoice} onChange={pickBrand}>
          <option value="" disabled>Select a brand…</option>
          {catalog?.brands.map((brand) => (
            <option key={brand.name} value={brand.name}>{brand.name}</option>
          ))}
          <option value={OTHER}>Other…</option>
        </select>
        {form.brandChoice === OTHER && (
          <input className="input mt-2" placeholder="Type the brand" value={form.make} onChange={update("make")} />
        )}
      </div>

      <div>
        <label className="label">Model *</label>
        {form.brandChoice && form.brandChoice !== OTHER ? (
          <>
            <select className="input" required value={form.modelChoice} onChange={pickModel}>
              <option value="" disabled>Select a model…</option>
              {models.map((model) => <option key={model} value={model}>{model}</option>)}
              <option value={OTHER}>Other…</option>
            </select>
            {form.modelChoice === OTHER && (
              <input className="input mt-2" placeholder="Type the model" value={form.model} onChange={update("model")} />
            )}
          </>
        ) : (
          <input className="input" placeholder="Type the model" value={form.model} onChange={update("model")} disabled={!form.brandChoice} />
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Year</label>
          <select className="input" value={form.year} onChange={update("year")}>
            <option value="">—</option>
            {catalog?.years.map((year) => <option key={year} value={year}>{year}</option>)}
          </select>
        </div>
        <div>
          <label className="label">Plate No.</label>
          <input className="input" value={form.registration_number} onChange={update("registration_number")} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="label">Colour</label>
          <input className="input" value={form.color} onChange={update("color")} />
        </div>
        <div>
          <label className="label">Fuel</label>
          <select className="input" value={form.fuel_type} onChange={update("fuel_type")}>
            {FUEL_TYPES.map((fuel) => (
              <option key={fuel} value={fuel}>{fuel[0].toUpperCase() + fuel.slice(1)}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="label">Current odometer (km)</label>
        <input className="input" type="number" min="0" value={form.current_odometer_km} onChange={update("current_odometer_km")} />
      </div>

      <div>
        <label className="label">VIN</label>
        <input className="input" value={form.vin} onChange={update("vin")} />
      </div>

      <div>
        <label className="label">Notes</label>
        <textarea className="input" rows={2} value={form.notes} onChange={update("notes")} />
      </div>

      <button className="btn-primary" disabled={loading}>
        {loading ? "Saving…" : isEdit ? "Save changes" : "Add car"}
      </button>
    </form>
  );
}
