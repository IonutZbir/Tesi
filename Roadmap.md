# Argomenti da studiare

## 1. **Aritmetica Modulare (Modulo p)**

* Operazioni modulo un numero primo: addizione, moltiplicazione, esponenziazione.
* Inversi modulari (es: trovare $x$ tale che $ax \equiv 1 \mod p$)
* Concetto di **gruppo ciclico** e **generatori**.

**Cosa studiare**:

* Teorema di Fermat
* Gruppo moltiplicativo modulo $p$: $\mathbb{Z}_p^*$

---

## 2. **Logaritmi Discreti**

* Il problema del logaritmo discreto: trovare $x$ tale che $g^x \equiv y \mod p$
* Perché è difficile? (problema "one-way" fondamentale per la sicurezza)

**Esempio**:

* Dato $g = 2$, $y = 11$, e $p = 23$, trovare $x$ tale che $2^x \equiv 11 \mod 23$

---

## 3. **Hash Function crittografiche (a livello base)**

* Proprietà: one-way, collision-resistant, ecc.
* Perché le usiamo nei protocolli di identificazione?
* SHA-256 come esempio concreto

---

## 4. **Protocolli di Zero-Knowledge (ZKP) - concetto base**

* Cosa significa "dimostrare di sapere qualcosa **senza rivelarla**"?
* Interazione: prove a tre fasi (commitment → challenge → response)

**Concetto chiave**:

* Prover vs Verifier
* Nessun osservatore può imparare il segreto

---

## 5. **Diffie-Hellman e Schnorr come evoluzione**

* Capire il parallelo: entrambi usano l’esponenziazione modulare
* Schnorr è più efficiente e sicuro (sotto certe assunzioni)
