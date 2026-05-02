import React, { useState } from 'react';
import axios from 'axios';
import { Upload, X, Loader2, CheckCircle2 } from 'lucide-react';

const PredictionForm: React.FC = () => {
  const [formData, setFormData] = useState({
    ring_size: '6.5',
    inner_diameter_mm: '',
    band_width_mm: '',
    band_thickness_mm: '',
    stone_length_mm: '',
    stone_width_mm: '',
    stone_ct: '',
    side_stone_count: '0',
    side_stone_ct: '0',
  });
  
  const [image, setImage] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImage(file);
      setPreview(URL.createObjectURL(file));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Submit clicked. Checking image...');
    if (!image) {
      console.error('No image selected.');
      setError('Please upload a ring image');
      return;
    }

    console.log('FormData:', formData);
    setLoading(true);
    setError(null);
    setResult(null);

    const data = new FormData();
    Object.entries(formData).forEach(([key, value]) => {
      if (value) data.append(key, value);
    });
    data.append('image', image);

    try {
      console.log('Sending request to backend...');
      const response = await axios.post('http://localhost:8000/api/v1/predict', data);
      console.log('Response received:', response.data);
      setResult(response.data);
    } catch (err: any) {
      console.error('Error during prediction:', err);
      setError(err.response?.data?.detail || 'Failed to get prediction. Please try again.');
    } finally {
      console.log('Request cycle complete.');
      setLoading(false);
    }
  };

  if (result) {
    const prediction = result.prediction || result;
    const similar_examples = result.similar_examples || [];

    return (
      <div className="space-y-6 animate-fadeInUp">
        <div className="flex items-center text-green-600 mb-4">
          <CheckCircle2 className="h-6 w-6 mr-2" />
          <h3 className="text-xl font-semibold">Prediction Ready</h3>
        </div>
        
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">14K Gold</span>
            <div className="text-3xl font-bold text-[#111827] mt-1">{prediction.predicted_weight_14k.toFixed(3)}g</div>
          </div>
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">18K Gold</span>
            <div className="text-3xl font-bold text-[#111827] mt-1">{prediction.predicted_weight_18k.toFixed(3)}g</div>
          </div>
        </div>

        <div className="mt-6">
          <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">AI Explanation</h4>
          <p className="text-gray-700 text-sm leading-relaxed bg-white border border-gray-100 p-4 rounded-xl shadow-sm italic">
            "{prediction.llm_explanation}"
          </p>
        </div>

        {similar_examples.length > 0 && (
          <div className="mt-8">
            <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4">Top 5 Similar Designs (RAG)</h4>
            <div className="space-y-3">
              {similar_examples.map((ex: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-white border border-gray-100 rounded-xl shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex-1">
                    <div className="text-sm font-bold text-gray-800">{ex.product_name || `Similar Ring #${idx + 1}`}</div>
                    <div className="text-xs text-gray-500">
                      Size: {ex.params?.ring_size || 'N/A'} | Stone: {ex.params?.stone_ct || 0}ct
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-accent">{ex.actual_weight}g</div>
                    <div className="text-[10px] text-gray-400">Match: {(ex.score * 100).toFixed(1)}%</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => {
            setResult(null);
            setFormData({
              ring_size: '',
              inner_diameter_mm: '',
              band_width_mm: '',
              band_thickness_mm: '',
              stone_length_mm: '',
              stone_width_mm: '',
              stone_ct: '',
              side_stone_count: '',
              side_stone_ct: '',
              karat: '18K',
              metal_color: 'Yellow'
            });
            setImage(null);
            setPreview(null);
          }}
          className="w-full mt-4 bg-[#111827] text-white py-3 rounded-xl font-semibold hover:bg-gray-800 transition-all transform hover:-translate-y-0.5 active:translate-y-0"
        >
          New Calculation
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Image Upload */}
      <div className="relative">
        <label className="block text-sm font-semibold text-gray-700 mb-2">Ring Design Image</label>
        {preview ? (
          <div className="relative rounded-2xl overflow-hidden aspect-video border-2 border-dashed border-gray-200 group">
            <img src={preview} alt="Preview" className="w-full h-full object-cover" />
            <button
              type="button"
              onClick={() => { setImage(null); setPreview(null); }}
              className="absolute top-2 right-2 p-1 bg-white/80 rounded-full text-gray-700 hover:bg-white transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        ) : (
          <label className="flex flex-col items-center justify-center w-full aspect-video border-2 border-dashed border-gray-200 rounded-2xl cursor-pointer hover:bg-gray-50 transition-colors bg-gray-50/50">
            <Upload className="h-10 w-10 text-gray-400 mb-2" />
            <span className="text-sm text-gray-500">Click to upload or drag and drop</span>
            <span className="text-xs text-gray-400 mt-1">PNG, JPG up to 10MB</span>
            <input type="file" className="hidden" onChange={handleImageChange} accept="image/*" />
          </label>
        )}
      </div>

      {/* Grid of inputs */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Ring Size (US)</label>
          <input
            type="number" step="0.25" name="ring_size" value={formData.ring_size} onChange={handleInputChange}
            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent focus:bg-white outline-none transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Band Width (mm)</label>
          <input
            type="number" step="0.1" name="band_width_mm" value={formData.band_width_mm} onChange={handleInputChange}
            placeholder="e.g. 2.0"
            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent focus:bg-white outline-none transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Stone Length (mm)</label>
          <input
            type="number" step="0.1" name="stone_length_mm" value={formData.stone_length_mm} onChange={handleInputChange}
            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent focus:bg-white outline-none transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1">Stone Width (mm)</label>
          <input
            type="number" step="0.1" name="stone_width_mm" value={formData.stone_width_mm} onChange={handleInputChange}
            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-accent focus:bg-white outline-none transition-all"
          />
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 text-sm rounded-xl border border-red-100">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-[#111827] text-white py-4 rounded-xl font-bold hover:bg-gray-800 transition-all transform hover:-translate-y-0.5 active:translate-y-0 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg shadow-gray-200"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
            Calculating Weight...
          </>
        ) : (
          'Predict Gold Weight'
        )}
      </button>
    </form>
  );
};

export default PredictionForm;
