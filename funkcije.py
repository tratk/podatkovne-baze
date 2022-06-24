import sqlite3 as dbapi
import datetime
from datumi import Datum

def izposodi(id_knjiga, id_clan, con):
    '''Doda izposojo v bazo.'''
    cur = con.cursor()
    d = datetime.datetime.now()
    datum = Datum(int(d.day), int(d.month), int(d.year)) #ustvari danasnji datum
    cur.execute("""INSERT INTO izposoja (knjiga, clan, datum_izposoje, zamudnina) 
                    VALUES (?, ?, ?, 0)""", (id_knjiga, id_clan, str(datum))) #doda v bazo
    con.commit()
    cur.close()


def izracunaj_zamudnino(d1, d2, marza = 0.1):
    '''Izracuna zamudnino glede na to, koliko dni je bila izposojena knjiga.'''
    razlika = d2.razlika(d1)
    if razlika <= 14:
        return 0
    else:
        return (razlika - 14) * marza


def vrni(id_izposoje, con):
    '''Vrne izposojeno knjigo in doda zamudnino.'''
    cur = con.cursor()
    d = datetime.datetime.now()
    datum = Datum(int(d.day), int(d.month), int(d.year)) #ustvari danasnji datum
    cur.execute("SELECT datum_izposoje FROM izposoja WHERE id = ?", (id_izposoje,)) #poisce datum izposoje
    d1 = cur.fetchone()[0].split('-')
    datum_izposoje = Datum(int(d1[2]), int(d1[1]), int(d1[0]))
    zamudnina = izracunaj_zamudnino(datum_izposoje, datum) #izracuna zamudnino
    cur.execute("""UPDATE izposoja SET datum_vracila = ?, zamudnina = ?
                WHERE id = ?""", (str(datum), round(zamudnina, 2), id_izposoje)) #doda datum vrnitve in zamudnino izposoji
    
    if zamudnina != 0:
        cur.execute("SELECT clan FROM izposoja WHERE id = ?", (id_izposoje,))
        clan = cur.fetchone()[0]
        cur.execute("SELECT dolg FROM clan WHERE id = ?", (clan,)) #poisce trenuten dolg clana
        dolg = float(cur.fetchone()[0])
        dolg += zamudnina
        cur.execute("UPDATE clan SET dolg = ? WHERE id = ?", (round(dolg, 2), clan)) #doda nov dolg
        
    con.commit()
    cur.close()

def poravnaj_dolg(id_clana, con):
    '''Poravna dolg clana'''
    cur = con.cursor()
    cur.execute("UPDATE clan set dolg = 0 WHERE id = ?", (str(id_clana),)) #postavi dolg na 0
    con.commit()
    cur.close()
    
def dodaj_clana(ime, priimek, starost, spol, con):
    '''Doda novega clana'''
    cur = con.cursor()
    cur.execute("""INSERT INTO clan (ime, priimek, starost, spol, dolg)
                    VALUES (?, ?, ?, ?, 0)""", (ime, priimek, starost, spol))
    con.commit()
    cur.close()

def dodaj_knjigo(naslov, avtor, zanr, leto_izdaje, zalozba, con):
    '''Doda novo knjigo'''
    cur = con.cursor()
    cur.execute("""INSERT INTO knjiga (naslov, avtor, zanr, leto_izdaje, zalozba)
                    VALUES (?, ?, ?, ?, ?)""", (naslov, avtor, zanr, leto_izdaje, zalozba))
    con.commit()
    cur.close()



def isci_knjigo(podatek, tabela, con):
    '''Poisce knjigo glede na vnesen podatek'''
    cur = con.cursor()
    cur.execute("SELECT * FROM knjiga LEFT JOIN izposoja ON knjiga.id = izposoja.knjiga WHERE "
                + tabela + "  like ? ", ('%' + podatek + '%',)) #da dobi se podatke o izposoji
    rezultat = cur.fetchall()
    cur.close()
    knjige = {}
    if not isinstance(rezultat, list):
        rezultat = [rezultat]
    for knjiga in rezultat: #doda ali je knjiga izposojena ali ne in odstrani podvojitve izposoj
        if knjiga[9] != None and knjiga[10] == None: #ima datum izposoje in nima datuma vracila
            izposoja = 'Izposojena'
        else:
            izposoja = 'Neizposojena'
        if knjiga[0] in knjige:
            if knjiga[6] == 'Neizposojena' and izposoja == 'Izposojena': #nasli novejso izposojo, ki ni se vrnjena
                knjige[knjiga[0]] = [knjiga[0], knjiga[1], knjiga[2], knjiga[3], knjiga[4], knjiga[5], izposoja]
        else:
            knjige[knjiga[0]] = [knjiga[0], knjiga[1], knjiga[2], knjiga[3], knjiga[4], knjiga[5], izposoja]
    return knjige

def poisci_clana(id_clana, con):
    '''Poisice clana glede na njegov id'''
    cur = con.cursor()
    cur.execute("SELECT * FROM clan WHERE id = ?", (id_clana,))
    clan = cur.fetchone()
    cur.close()
    return clan

def poisci_clana_ime(niz, tabela, con):
    '''Poisce clane po imenu ali priimku.'''
    cur = con.cursor()
    if tabela == 'ime':
        cur.execute("SELECT * FROM clan WHERE ime like ?", ('%' + niz + '%',))
    else:
        cur.execute("SELECT * FROM clan WHERE priimek like ?", ('%' + niz + '%',))
    clani = cur.fetchall()
    cur.close()
    return clani

def poisci_izposoje_clana(id_clana, con, vrnjene = True):
    '''Poisce vse izposoje ali trenutne izposoje clana.'''
    cur = con.cursor()
    cur.execute("SELECT * FROM izposoja WHERE izposoja.clan = ?", (id_clana,))
    podatki = cur.fetchall()
    cur.close()
    if not vrnjene:
        return podatki
    izposoje = []
    for el in podatki:
        if el[4] is not None:
            izposoje.append(el)
    return izposoje

def podatki_knjige(id, con):
    '''Poisce podatke o doloceni knjigi.'''
    cur = con.cursor()
    cur.execute("SELECT * FROM knjiga WHERE id = ?", (id,))
    knjiga = cur.fetchone()
    cur.close()
    return knjiga

def preveri(id_knjige, con):
    '''Preveri, ali je knjiga z id_knjige v bazi ali ce je trenutno izposojena.'''
    cur = con.cursor()
    cur.execute("SELECT * FROM knjiga WHERE id = ?", (id_knjige,))
    knjiga = cur.fetchone()
    izposojena, obstaja = False, False
    if knjiga is not None: #id je v bazi
        obstaja = True
        cur.execute("SELECT * FROM izposoja WHERE knjiga = ?", (id_knjige,))
        izposoja = cur.fetchall()
        for el in izposoja:
            if el[3] is not None and el[4] is None: #knjiga trenutno izposojena
                izposojena = True
                break                
    cur.close()
    return (obstaja, izposojena)