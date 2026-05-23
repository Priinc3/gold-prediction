import { API_BASE_URL } from '../config';
import React, { useState } from 'react';
import axios from 'axios';
import { Upload, CheckCircle2, AlertCircle, Loader2, X, Search, Trash2 } from 'lucide-react';

interface FormData {
  ring_size: string;
  inner_diameter_mm: string;
  band_width_mm: string;
  band_thickness_mm: string;
  stone_length_mm: string;
  stone_width_mm: string;
  stone_ct: string;
  side_stone_count: string;
  side_stone_ct: string;
  karat: string;
  metal_color: string;
}

const INDIAN_RING_SIZES: Record<number, number> = {
  1: 13.1, 2: 13.3, 3: 13.7, 4: 13.9, 5: 14.3,
  6: 14.7, 7: 15.1, 8: 15.3, 9: 15.5, 10: 15.9,
  11: 16.3, 12: 16.5, 13: 16.9, 14: 17.3, 15: 17.5,
  16: 17.9, 17: 18.1, 18: 18.5, 19: 18.8, 20: 19.2,
  21: 19.4, 22: 19.8, 23: 20.0, 24: 20.4, 25: 20.6,
  26: 21.0, 27: 21.4, 28: 21.6, 29: 22.0, 30: 22.3
};

const getDiameterForSize = (size: number, standard: 'Indian' | 'US') => {
  if (standard === 'Indian') {
    const idx = Math.round(size);
    return INDIAN_RING_SIZES[idx] || 16.5;
  } else {
    return (size * 0.8128) + 11.6332;
  }
};

const PredictionForm: React.FC = () => {
  const [formData, setFormData] = useState<FormData>({
    ring_size: '',
    inner_diameter_mm: '',
    band_width_mm: '',
    band_thickness_mm: '',
    stone_length_mm: '',
    stone_width_mm: '',
    stone_ct: '',
    side_stone_count: '0',
    side_stone_ct: '0.0',
    karat: '18K',
    metal_color: 'Yellow'
  });

  const [images, setImages] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [actualWeight, setActualWeight] = useState('');
  const [actualKarat, setActualKarat] = useState('18K');
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [targetSizes, setTargetSizes] = useState<number[]>([]);
  const [sizeStandard, setSizeStandard] = useState<'Indian' | 'US'>('Indian');
  const [displaySize, setDisplaySize] = useState<number>(12); // New: Default to Indian women's size 12
  const [imageSource, setImageSource] = useState<'upload' | 'url'>('upload'); // New: Image sourcing choice
  const [imageUrl, setImageUrl] = useState(''); // New: Pasted image URL

  const toggleSize = (size: number) => {
    if (targetSizes.includes(size)) {
      setTargetSizes(targetSizes.filter(s => s !== size));
    } else {
      setTargetSizes([...targetSizes, size]);
    }
  };

  // Helper for live scaling logic in UI
  const getScaledWeight = (baseWeight: number, baseSize: number, targetSize: number) => {
    const dBase = getDiameterForSize(baseSize, sizeStandard);
    const dTarget = getDiameterForSize(targetSize, sizeStandard);
    return baseWeight * (dTarget / dBase);
  };

  const handleDeleteSimilar = async (itemId: string) => {
    if (!window.confirm("Are you sure you want to remove this ring from the AI's memory?")) return;
    
    try {
      await axios.delete(`${API_BASE_URL}/rag/${itemId}`);
      // Update local state to remove the item from view
      if (result) {
        const updatedSimilar = (result.similar_examples || []).filter((ex: any) => ex.product_id !== itemId);
        setResult({ ...result, similar_examples: updatedSimilar });
      }
    } catch (err) {
      console.error('Delete failed:', err);
      alert("Failed to remove item from memory.");
    }
  };

  const handleFeedback = async (isCorrect: boolean) => {
    if (!result) return;
    
    setIsSubmittingFeedback(true);
    try {
      await axios.post(API_BASE_URL + '/feedback', {
        prediction_id: result.prediction?.id || result.id,
        is_correct: isCorrect,
        actual_weight_g: actualWeight ? parseFloat(actualWeight) : null,
        actual_karat: actualKarat,
        actual_diamond_carat: formData.stone_ct ? parseFloat(formData.stone_ct) : 0
      });
      setFeedbackSubmitted(true);
    } catch (err) {
      console.error('Feedback failed:', err);
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    const newImages = [...images, ...files].slice(0, 3);
    setImages(newImages);

    const newPreviews: string[] = [];
    newImages.forEach(file => {
      const reader = new FileReader();
      reader.onloadend = () => {
        newPreviews.push(reader.result as string);
        if (newPreviews.length === newImages.length) {
          setPreviews(newPreviews);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const removeImage = (index: number) => {
    const newImages = images.filter((_, i) => i !== index);
    const newPreviews = previews.filter((_, i) => i !== index);
    setImages(newImages);
    setPreviews(newPreviews);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (imageSource === 'upload' && images.length === 0) {
      setError('Please upload at least one ring image');
      return;
    }
    if (imageSource === 'url' && !imageUrl.trim()) {
      setError('Please enter a valid image URL');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);
    setFeedbackSubmitted(false);
    setActualWeight('');

    const data = new FormData();
    Object.entries(formData).forEach(([key, value]) => {
      if (value) data.append(key, value);
    });
    
    // Add ring size standard selection
    data.append('ring_size_standard', sizeStandard);
    
    // Add multiple target sizes
    if (targetSizes.length > 0) {
      data.append('target_sizes', JSON.stringify(targetSizes));
    }
    
    if (imageSource === 'url') {
      data.append('image_url', imageUrl.trim());
    } else {
      images.forEach(img => {
        data.append('images', img);
      });
    }

    try {
      const response = await axios.post(API_BASE_URL + '/predict', data);
      setResult(response.data);
      if (formData.ring_size) setDisplaySize(parseFloat(formData.ring_size));
      else setDisplaySize(7);
    } catch (err: any) {
      console.error(err);
      let errorMsg = 'Failed to get prediction. Please try again.';
      if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
          errorMsg = detail;
        } else if (Array.isArray(detail)) {
          errorMsg = detail
            .map((d: any) => {
              const field = d.loc ? d.loc.filter((l: any) => l !== 'body').join('.') : '';
              return field ? `${field}: ${d.msg}` : d.msg;
            })
            .join(', ');
        } else if (typeof detail === 'object') {
          errorMsg = detail.message || JSON.stringify(detail);
        }
      } else if (err.message) {
        errorMsg = err.message;
      }
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    const prediction = result.prediction || result;
    const similar_examples = result.similar_examples || [];

    const baseSize = parseFloat(formData.ring_size) || 7;

    return (
      <div className="space-y-6 animate-fadeInUp">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center text-green-600">
            <CheckCircle2 className="h-6 w-6 mr-2" />
            <h3 className="text-xl font-semibold">Prediction Ready</h3>
          </div>
          <div className="flex items-center bg-gray-50 px-3 py-1.5 rounded-full border border-gray-100">
            <span className="text-[10px] font-bold text-gray-400 uppercase mr-2">Viewing Size</span>
            <span className="text-sm font-bold text-accent">{sizeStandard} {displaySize}</span>
          </div>
        </div>

        {/* DYNAMIC SIZE TOGGLE ON RESULTS PAGE */}
        <div className="bg-white border border-gray-100 p-4 rounded-2xl shadow-sm mb-6">
          <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mb-3 text-center">Adjust Ring Size Locally ({sizeStandard})</div>
          <div className="flex flex-wrap justify-center gap-2">
            {(sizeStandard === 'Indian' ? [9, 10, 11, 12, 13, 14, 15, 16, 17, 18] : [5, 6, 7, 8, 9, 10, 11, 12]).map(size => (
              <button
                key={size}
                onClick={() => setDisplaySize(size)}
                className={`px-4 py-2 rounded-xl text-xs font-bold transition-all border ${
                  displaySize === size
                    ? 'bg-accent border-accent text-white shadow-lg scale-105'
                    : 'bg-white border-gray-100 text-gray-500 hover:border-accent/30'
                }`}
              >
                Size {size}
              </button>
            ))}
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100 relative overflow-hidden group">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">14K Gold Range</span>
            <div className="text-xl font-bold text-[#111827] mt-1">
              {getScaledWeight(prediction.min_weight_14k, baseSize, displaySize).toFixed(3)}g - {getScaledWeight(prediction.max_weight_14k, baseSize, displaySize).toFixed(3)}g
            </div>
          </div>
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">18K Gold Range</span>
            <div className="text-xl font-bold text-[#111827] mt-1">
              {getScaledWeight(prediction.min_weight_18k, baseSize, displaySize).toFixed(3)}g - {getScaledWeight(prediction.max_weight_18k, baseSize, displaySize).toFixed(3)}g
            </div>
          </div>
          <div className="bg-gray-50 p-4 rounded-xl border border-gray-100">
            <span className="text-xs text-gray-500 uppercase tracking-wider font-bold">22K Gold Range</span>
            <div className="text-xl font-bold text-[#111827] mt-1">
              {getScaledWeight(prediction.min_weight_22k, baseSize, displaySize).toFixed(3)}g - {getScaledWeight(prediction.max_weight_22k, baseSize, displaySize).toFixed(3)}g
            </div>
          </div>
        </div>

        <div className="bg-accent/5 border border-accent/10 rounded-xl p-4 flex justify-between items-center">
          <div>
            <span className="text-xs text-accent uppercase tracking-wider font-bold">Estimated Base Volume</span>
            <div className="text-lg font-bold text-[#111827]">{prediction.estimated_volume_mm3?.toFixed(2)} mm³</div>
          </div>
          <div className="text-right">
            <span className="text-[10px] text-gray-400 block uppercase">Manufacturing Cap</span>
            <span className="text-sm font-bold text-green-600">Safe Buffer Applied</span>
          </div>
        </div>

        <div className="mt-6">
          <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-2">AI Explanation</h4>
          <p className="text-gray-700 text-sm leading-relaxed bg-white border border-gray-100 p-4 rounded-xl shadow-sm italic">
            "{prediction.llm_explanation}"
          </p>
        </div>

        {prediction.size_variations && prediction.size_variations.length > 0 && (
          <div className="mt-8 overflow-hidden border border-gray-100 rounded-2xl shadow-sm">
            <div className="bg-gray-50 p-4 border-b border-gray-100">
              <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider">Weight Variations by Size</h4>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="bg-white text-gray-400 uppercase text-[10px] font-bold tracking-widest">
                    <th className="px-6 py-4">Ring Size</th>
                    <th className="px-6 py-4">14K Weight</th>
                    <th className="px-6 py-4">18K Weight</th>
                    <th className="px-6 py-4">22K Weight</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {prediction.size_variations.map((v: any, idx: number) => (
                    <tr key={idx} className="bg-white hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 font-bold text-gray-900">{sizeStandard} {v.ring_size}</td>
                      <td className="px-6 py-4 text-gray-600">{v.weight_14k.toFixed(3)}g</td>
                      <td className="px-6 py-4 text-accent font-semibold">{v.weight_18k.toFixed(3)}g</td>
                      <td className="px-6 py-4 text-gray-600">{v.weight_22k.toFixed(3)}g</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* FEEDBACK SECTION */}
        <div className="mt-8 bg-white border border-gray-100 rounded-2xl p-6 shadow-sm">
          <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center">
            <CheckCircle2 className="h-4 w-4 mr-2 text-accent" />
            Was this prediction accurate?
          </h4>
          
          {!feedbackSubmitted ? (
            <div className="space-y-4">
              <div className="flex space-x-4">
                <button 
                  onClick={() => handleFeedback(true)}
                  className="flex-1 py-3 px-4 rounded-xl border-2 border-green-500 text-green-600 font-bold hover:bg-green-50 transition-colors"
                >
                  Yes, Accurate
                </button>
                <button 
                  onClick={() => handleFeedback(false)}
                  className="flex-1 py-3 px-4 rounded-xl border-2 border-red-500 text-red-600 font-bold hover:bg-red-50 transition-colors"
                >
                  No, Needs Fix
                </button>
              </div>
              
              <div className="pt-4 border-t border-gray-50">
                <p className="text-xs text-gray-500 mb-3">Provide actual data to improve the AI's future accuracy:</p>
                <div className="grid grid-cols-2 gap-4">
                  <input 
                    type="number" 
                    placeholder="Actual Weight (g)" 
                    value={actualWeight}
                    onChange={(e) => setActualWeight(e.target.value)}
                    className="p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-accent text-sm"
                  />
                  <select 
                    value={actualKarat}
                    onChange={(e) => setActualKarat(e.target.value)}
                    className="p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-accent text-sm"
                  >
                    <option value="14K">14K</option>
                    <option value="18K">18K</option>
                    <option value="22K">22K</option>
                    <option value="24K">24K</option>
                  </select>
                </div>
                <button 
                  onClick={() => handleFeedback(false)}
                  disabled={!actualWeight || isSubmittingFeedback}
                  className="w-full mt-4 bg-accent text-white py-3 rounded-xl font-bold hover:bg-accent/90 transition-all disabled:opacity-50"
                >
                  {isSubmittingFeedback ? 'Syncing with Vector DB...' : 'Submit Actual Data'}
                </button>
              </div>
            </div>
          ) : (
            <div className="bg-green-50 text-green-700 p-4 rounded-xl text-center text-sm font-medium border border-green-100">
              Thank you! This data has been converted to design density and re-indexed into Pinecone to improve future RAG results.
            </div>
          )}
        </div>

        {similar_examples.length > 0 && (
          <div className="mt-8">
            <h4 className="text-sm font-bold text-gray-500 uppercase tracking-wider mb-4 flex items-center">
              <Search className="h-4 w-4 mr-2" />
              Similar Designs from History
            </h4>
            <div className="grid grid-cols-1 gap-3">
              {similar_examples.map((ex: any, idx: number) => (
                <div key={idx} className={`flex items-center justify-between p-3 bg-white border rounded-xl shadow-sm hover:shadow-md transition-shadow ${ex.score >= 0.9 ? 'border-accent ring-1 ring-accent/20' : 'border-gray-100'}`}>
                  <div className="flex-1">
                    <div className="flex items-center">
                      <div className="text-sm font-bold text-gray-800">{ex.product_name || `Similar Ring #${idx + 1}`}</div>
                      {ex.score >= 0.9 && (
                        <span className="ml-2 px-1.5 py-0.5 bg-accent text-[10px] text-white font-bold rounded uppercase">Priority</span>
                      )}
                    </div>
                    <div className="text-xs text-gray-500">
                      Size: {ex.params?.ring_size || 'N/A'} | Stone: {ex.params?.stone_ct || 0}ct | Vol: {ex.actual_volume_mm3?.toFixed(1)}mm³
                    </div>
                  </div>
                  <div className="text-right flex flex-col items-end">
                    <div className="text-sm font-bold text-accent">{ex.actual_weight}g ({ex.karat || ex.params?.karat})</div>
                    <div className="text-[10px] text-gray-400">Match: {(ex.score * 100).toFixed(1)}% | ID: {ex.product_id?.substring(0, 8)}</div>
                    <button 
                      onClick={() => handleDeleteSimilar(ex.product_id)}
                      className="mt-1 p-1 text-gray-300 hover:text-red-500 transition-colors"
                      title="Remove from memory"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={() => {
            setResult(null);
            setFeedbackSubmitted(false);
            setActualWeight('');
            setActualKarat('18K');
            setFormData({
              ring_size: '',
              inner_diameter_mm: '',
              band_width_mm: '',
              band_thickness_mm: '',
              stone_length_mm: '',
              stone_width_mm: '',
              stone_ct: '',
              side_stone_count: '0',
              side_stone_ct: '0.0',
              karat: '18K',
              metal_color: 'Yellow'
            });
            setImages([]);
            setPreviews([]);
            setTargetSizes([]);
            setImageUrl('');
            setImageSource('upload');
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
      {/* Image Sourcing Choice */}
      <div className="space-y-4">
        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">
          Image Input Method
        </label>
        <div className="flex gap-2 p-1 bg-gray-50 border border-gray-200/50 rounded-xl">
          <button
            type="button"
            onClick={() => {
              setImageSource('upload');
              setError(null);
            }}
            className={`flex-1 py-2.5 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              imageSource === 'upload'
                ? 'bg-accent border-accent text-white shadow-sm'
                : 'bg-transparent text-gray-400 hover:text-gray-600'
            }`}
          >
            <Upload className="h-3.5 w-3.5" />
            Upload Photos
          </button>
          <button
            type="button"
            onClick={() => {
              setImageSource('url');
              setError(null);
            }}
            className={`flex-1 py-2.5 text-xs font-bold rounded-lg transition-all flex items-center justify-center gap-1.5 ${
              imageSource === 'url'
                ? 'bg-accent border-accent text-white shadow-sm'
                : 'bg-transparent text-gray-400 hover:text-gray-600'
            }`}
          >
            <Search className="h-3.5 w-3.5" />
            Paste Image URL
          </button>
        </div>
      </div>

      {/* Conditionally Render Input Form */}
      {imageSource === 'upload' ? (
        <div className="space-y-4 animate-fadeInUp">
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">
            Ring Images (Up to 3, multi-angle recommended)
          </label>
          
          <div className="grid grid-cols-3 gap-4">
            {previews.map((preview, idx) => (
              <div key={idx} className="relative aspect-square rounded-xl overflow-hidden border border-gray-200 shadow-sm group">
                <img src={preview} alt={`Preview ${idx + 1}`} className="w-full h-full object-cover" />
                <button
                  type="button"
                  onClick={() => removeImage(idx)}
                  className="absolute top-1 right-1 p-1 bg-white/90 rounded-full text-red-500 hover:bg-white transition-colors shadow-sm"
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            ))}
            
            {images.length < 3 && (
              <label className="flex flex-col items-center justify-center aspect-square border-2 border-dashed border-gray-200 rounded-xl cursor-pointer hover:bg-gray-50 hover:border-accent transition-all group">
                <Upload className="h-6 w-6 text-gray-400 group-hover:text-accent group-hover:scale-110 transition-all" />
                <span className="text-[10px] text-gray-400 font-bold uppercase mt-1">Add Photo</span>
                <input type="file" className="hidden" onChange={handleImageChange} accept="image/*" multiple />
              </label>
            )}
          </div>
        </div>
      ) : (
        <div className="space-y-4 animate-fadeInUp">
          <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">
            Remote Image URL
          </label>
          <input
            type="url"
            placeholder="Paste direct image link (e.g., https://example.com/ring.jpg)"
            value={imageUrl}
            onChange={(e) => setImageUrl(e.target.value)}
            className="w-full p-3.5 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-accent transition-all text-sm font-medium"
          />
          {imageUrl && imageUrl.trim().startsWith('http') && (
            <div className="space-y-2 animate-scaleIn">
              <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest block ml-1">Live Preview</span>
              <div className="relative w-40 aspect-square rounded-xl overflow-hidden border border-gray-200 shadow-sm">
                <img 
                  src={imageUrl} 
                  alt="URL Preview" 
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    (e.target as HTMLImageElement).src = "https://images.unsplash.com/photo-1599643478518-a784e5dc4c8f?q=80&w=256&auto=format&fit=crop";
                  }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* SIZE STANDARD SELECTOR TABS */}
      <div className="mb-4">
        <label className="block text-xs font-bold text-gray-500 uppercase mb-2 ml-1">Size Standard</label>
        <div className="flex gap-2 p-1 bg-gray-50 border border-gray-200/50 rounded-xl">
          <button
            type="button"
            onClick={() => {
              setSizeStandard('Indian');
              setFormData({ ...formData, ring_size: '12' });
              setDisplaySize(12);
              setTargetSizes([]);
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
              sizeStandard === 'Indian'
                ? 'bg-accent border-accent text-white shadow-sm'
                : 'bg-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            🇮🇳 Indian Standard
          </button>
          <button
            type="button"
            onClick={() => {
              setSizeStandard('US');
              setFormData({ ...formData, ring_size: '7' });
              setDisplaySize(7);
              setTargetSizes([]);
            }}
            className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all ${
              sizeStandard === 'US'
                ? 'bg-accent border-accent text-white shadow-sm'
                : 'bg-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            🇺🇸 US Standard
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1 ml-1">Base Size ({sizeStandard})</label>
          <input
            type="number" step="0.25" name="ring_size" value={formData.ring_size} onChange={handleInputChange}
            placeholder={sizeStandard === 'Indian' ? 'Default: 12' : 'Default: 7'}
            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-accent transition-all"
          />
        </div>
        <div>
          <label className="block text-xs font-bold text-gray-500 uppercase mb-1 ml-1">Stone Carat (ct)</label>
          <input
            type="number" step="0.01" name="stone_ct" value={formData.stone_ct} onChange={handleInputChange}
            placeholder="Optional"
            className="w-full p-3 bg-gray-50 border border-gray-200 rounded-xl outline-none focus:ring-2 focus:ring-accent transition-all"
          />
        </div>
      </div>

      <div className="space-y-2">
        <label className="block text-xs font-bold text-gray-500 uppercase tracking-wider ml-1">
          Calculate for additional sizes ({sizeStandard}):
        </label>
        <div className="flex flex-wrap gap-2">
          {(sizeStandard === 'Indian' ? [9, 10, 11, 12, 13, 14, 15, 16, 17, 18] : [5, 6, 7, 8, 9, 10, 11, 12]).map(size => (
            <button
              key={size}
              type="button"
              onClick={() => toggleSize(size)}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                targetSizes.includes(size)
                  ? 'bg-accent border-accent text-white shadow-md'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-accent'
              }`}
            >
              Size {size}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="p-4 bg-red-50 text-red-700 rounded-xl flex items-center text-sm border border-red-100">
          <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-[#111827] text-white py-4 rounded-xl font-bold hover:bg-gray-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center shadow-lg shadow-gray-200"
      >
        {loading ? (
          <>
            <Loader2 className="h-5 w-5 mr-2 animate-spin" />
            Calculating Volume & Weight...
          </>
        ) : (
          "Calculate Gold Weight"
        )}
      </button>
    </form>
  );
};

export default PredictionForm;
