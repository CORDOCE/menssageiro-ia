---
name: hipotese
description: Investiga bug, comportamento inesperado ou decisão técnica incerta pelo método falsificacionista (Popper) — observação reproduzível, hipótese falseável, predição, experimento mínimo executável (teste que falha primeiro), refutação ou corroboração. Proíbe concluir sem experimento. Acione com /hipotese.
---

# Skill: Hipótese (método científico)

Objetivo: chegar à causa com **evidência executável**, não com a explicação mais plausível.

## Processo
1. **Observação reproduzível.** Escreva o comando/entrada, a saída obtida e a esperada. Se não reproduz, pare aqui:
   o primeiro trabalho é reproduzir (teste, script ou log com `correlation_id`).
2. **Liste 2–4 hipóteses concorrentes.** Para cada uma: "se for verdadeira, observaremos X; se for falsa, observaremos Y".
   Descarte as que não têm Y (não falseáveis).
3. **Ordene** por (probabilidade × custo baixo do experimento). Comece pela mais barata de refutar.
4. **Experimento mínimo:** uma variável por vez. Preferência: teste automatizado que falha agora (red).
   Alternativas: script isolado, consulta ao banco de staging, log adicional temporário.
5. **Rode e registre** o resultado bruto (trecho curto da saída).
6. **Conclua:**
   - Refutada → registre em "Hipóteses descartadas" e volte ao passo 3.
   - Corroborada → corrija; o teste passa (green); mantenha o teste como guarda; rode a suíte afetada.
7. **Tente refutar a correção:** um caso de borda ou entrada adversa que ainda quebraria. Se achar, novo ciclo.

## Saída
```
Observação: ...
Hipóteses: H1 (refutada por ...), H2 (corroborada por ...), ...
Experimento decisivo: <teste/comando> → <resultado>
Correção: <arquivo(s)> · Guarda: <teste>
Hipóteses descartadas: ...
```

## Proibido
- Corrigir antes de reproduzir.
- Declarar causa sem experimento que pudesse tê-la refutado.
- Mudar várias coisas de uma vez e atribuir o efeito a uma delas.
