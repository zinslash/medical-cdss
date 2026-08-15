import { useState } from 'react';
import { StyleSheet, Text, View, Button, Image, ActivityIndicator, ScrollView } from 'react-native';
import * as ImagePicker from 'expo-image-picker';

export default function App() {
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const pickImage = async () => {
    let result = await ImagePicker.launchImageLibraryAsync({
  mediaTypes: ['images'],
      allowsEditing: true,
      quality: 1,
    });

    if (!result.canceled) {
      setImage(result.assets[0].uri);
      setResult(null);
    }
  };

  const analyzeImage = async () => {
    if (!image) return;
    setLoading(true);

    let formData = new FormData();
    formData.append('patient_id', 'mobile_test_001');
    formData.append('file', {
      uri: image,
      name: 'scan.jpg',
      type: 'image/jpeg',
    });

   try {
     const response = await fetch('https://legibly-duty-substance.ngrok-free.dev/analyze', {
        method: 'POST',
        body: formData,
        headers: {
            'ngrok-skip-browser-warning': 'true'
        },
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error(error);
      alert("Failed to connect to backend. Is Ngrok and Python running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>AI Medical Triage</Text>

      <Button title="Select X-Ray from Gallery" onPress={pickImage} />

      {image && (
        <Image source={{ uri: image }} style={styles.image} />
      )}

      {image && !loading && (
        <View style={{ marginTop: 20 }}>
            <Button title="Run AI Analysis" onPress={analyzeImage} color="green" />
        </View>
      )}

      {loading && <ActivityIndicator size="large" color="#0000ff" style={{ marginTop: 20 }} />}

      {result && (
        <View style={styles.resultBox}>
          <Text style={styles.boldText}>Organ Detected: {result.scan_type_detected}</Text>
          <Text style={styles.boldText}>Diagnosis: {result.diagnosis}</Text>
          <Text>Confidence: {result.confidence}%</Text>
          {/* Safe chaining just in case the backend formatting changes */}
          <Text style={{ marginTop: 10, fontStyle: 'italic' }}>{result.clinical_data?.triage || result.triage}</Text>

          {/* --- PREVENTIVE CARE SECTION --- */}
          <View style={{ marginTop: 15, padding: 12, backgroundColor: '#f0f8ff', borderRadius: 8 }}>
            <Text style={styles.boldText}>Standard Preventive Care:</Text>
            {result.preventive_care ? (
                result.preventive_care.map((care, index) => (
                    <Text key={index} style={{ marginTop: 4, fontSize: 14 }}>• {care}</Text>
                ))
            ) : (
                <View>
                    <Text style={{ marginTop: 4, fontSize: 14 }}>• Maintain a healthy, balanced diet and stay hydrated.</Text>
                    <Text style={{ marginTop: 4, fontSize: 14 }}>• Engage in regular, moderate physical activity.</Text>
                    <Text style={{ marginTop: 4, fontSize: 14 }}>• Ensure adequate sleep and manage stress levels.</Text>
                    <Text style={{ marginTop: 4, fontSize: 14 }}>• Keep up with routine medical check-ups.</Text>
                </View>
            )}
          </View>
          {/* ----------------------------------- */}

          {result.heatmap && (
              <Image
                source={{ uri: `data:image/jpeg;base64,${result.heatmap}` }}
                style={styles.heatmap}
              />
          )}
        </View>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flexGrow: 1, backgroundColor: '#f4f7f6', alignItems: 'center', padding: 30, paddingTop: 60 },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 20 },
  image: { width: 250, height: 250, marginTop: 20, borderRadius: 10 },
  heatmap: { width: 250, height: 250, marginTop: 20, borderRadius: 10, borderWidth: 2, borderColor: 'red' },
  resultBox: { marginTop: 30, padding: 20, backgroundColor: 'white', borderRadius: 10, width: '100%', shadowOpacity: 0.1, elevation: 3 },
  boldText: { fontWeight: 'bold', fontSize: 16, marginBottom: 5 }
});

