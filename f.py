# (¬(¬(A ⊕ C) → B) ⊕ ¬(C→A)  ⊕ B)∧D

s1 = "¬A∩¬C∩D∪¬B∩¬C∩D∪A∩¬B∩¬C∪¬A∩B"
print(s1.replace("∩", "*").replace("∪", "+"))
# print(s1.replace("*", "∩").replace("+", "∪"))
"¬A*¬B*D+¬A*¬C*D+¬C*B*D+C*¬B*D+A*B*D+A*C*D"
"¬A*¬B*D+C*¬B*D+A*B*D"

"¬A*¬C*D+C*¬B*D+A*C*D"
