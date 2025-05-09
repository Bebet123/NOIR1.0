// Generazione di una coppia di chiavi RSA utilizzando Web Crypto API
async function generateRSAKeyPair() {
    try {
      // Definizione delle specifiche della chiave RSA (2048 bit è una dimensione sicura comune)
      const keyPairOptions = {
        name: "RSA-OAEP",
        modulusLength: 2048, // Lunghezza della chiave in bit
        publicExponent: new Uint8Array([1, 0, 1]), // 65537
        hash: "SHA-256"
      };
      
      // Generazione della coppia di chiavi
      console.log("Generazione delle chiavi RSA in corso...");
      const keyPair = await window.crypto.subtle.generateKey(
        keyPairOptions,
        true, // Chiavi esportabili
        ["encrypt", "decrypt"] // Utilizzo previsto delle chiavi
      );
      
      console.log("Chiavi RSA generate con successo!");
      
      // Esportazione della chiave pubblica in formato spki
      const publicKeyExported = await window.crypto.subtle.exportKey(
        "spki", // SubjectPublicKeyInfo (formato standard)
        keyPair.publicKey
      );
      
      // Esportazione della chiave privata in formato pkcs8
      const privateKeyExported = await window.crypto.subtle.exportKey(
        "pkcs8", // PKCS #8 (formato standard)
        keyPair.privateKey
      );
      
      // Conversione in Base64 per una rappresentazione leggibile
      const publicKeyBase64 = arrayBufferToBase64(publicKeyExported);
      const privateKeyBase64 = arrayBufferToBase64(privateKeyExported);
      
      // Formattazione in PEM (formato comune per le chiavi)
      const publicKeyPEM = formatAsPEM(publicKeyBase64, "PUBLIC KEY");
      const privateKeyPEM = formatAsPEM(privateKeyBase64, "PRIVATE KEY");
      
      return {
        publicKey: publicKeyPEM,
        privateKey: privateKeyPEM
      };
    } catch (error) {
      console.error("Errore durante la generazione delle chiavi RSA:", error);
      throw error;
    }
  }
  
  // Funzione per convertire un ArrayBuffer in una stringa Base64
  function arrayBufferToBase64(buffer) {
    const byteArray = new Uint8Array(buffer);
    let binaryString = "";
    for (let i = 0; i < byteArray.byteLength; i++) {
      binaryString += String.fromCharCode(byteArray[i]);
    }
    return btoa(binaryString);
  }
  
  // Funzione per formattare una stringa Base64 nel formato PEM
  function formatAsPEM(base64Key, label) {
    // Suddivisione in righe di 64 caratteri
    const formattedKey = base64Key.match(/.{1,64}/g).join("\n");
    return `-----BEGIN ${label}-----\n${formattedKey}\n-----END ${label}-----`;
  }
  
  // Esempio di utilizzo
  async function main() {
    try {
      const keyPair = await generateRSAKeyPair();
      
      console.log("Chiave pubblica (PEM):");
      console.log(keyPair.publicKey);
      
      console.log("\nChiave privata (PEM):");
      console.log(keyPair.privateKey);
    } catch (error) {
      console.error("Si è verificato un errore:", error);
    }
  }
  
  // Esegui la funzione principale
  main();