#include <iostream>
using namespace std;

int convertirAQ14(float valor) {
    float escalado = valor * 16384.0f;

    if (escalado >= 0.0f) {
        return (int)(escalado + 0.5f);
    } else {
        return (int)(escalado - 0.5f);
    }
}


int main(){
    float resultado[91];
    int Q1_14[91];
    resultado[0] = 0.000000000000000;
    resultado[1] = 0.017452406437284;
    resultado[2] = 0.034899496702501;
    resultado[3] = 0.052335956242944;
    resultado[4] = 0.069756473744125;
    resultado[5] = 0.087155742747658;
    resultado[6] = 0.104528463267653;
    resultado[7] = 0.121869343405147;
    resultado[8] = 0.139173100960065;
    resultado[9] = 0.156434465040231;
    resultado[10] = 0.173648177666930;
    resultado[11] = 0.190808995376545;
    resultado[12] = 0.207911690817759;
    resultado[13] = 0.224951054343865;
    resultado[14] = 0.241921895599668;
    resultado[15] = 0.258819045102521;
    resultado[16] = 0.275637355816999;
    resultado[17] = 0.292371704722737;
    resultado[18] = 0.309016994374947;
    resultado[19] = 0.325568154457157;
    resultado[20] = 0.342020143325669;
    resultado[21] = 0.358367949545300;
    resultado[22] = 0.374606593415912;
    resultado[23] = 0.390731128489274;
    resultado[24] = 0.406736643075800;
    resultado[25] = 0.422618261740699;
    resultado[26] = 0.438371146789077;
    resultado[27] = 0.453990499739547;
    resultado[28] = 0.469471562785891;
    resultado[29] = 0.484809620246337;
    resultado[30] = 0.500000000000000;
    resultado[31] = 0.515038074910054;
    resultado[32] = 0.529919264233205;
    resultado[33] = 0.544639035015027;
    resultado[34] = 0.559192903470747;
    resultado[35] = 0.573576436351046;
    resultado[36] = 0.587785252292473;
    resultado[37] = 0.601815023152048;
    resultado[38] = 0.615661475325658;
    resultado[39] = 0.629320391049837;
    resultado[40] = 0.642787609686539;
    resultado[41] = 0.656059028990507;
    resultado[42] = 0.669130606358858;
    resultado[43] = 0.681998360062498;
    resultado[44] = 0.694658370458997;
    resultado[45] = 0.707106781186548;
    resultado[46] = 0.719339800338651;
    resultado[47] = 0.731353701619170;
    resultado[48] = 0.743144825477394;
    resultado[49] = 0.754709580222772;
    resultado[50] = 0.766044443118978;
    resultado[51] = 0.777145961456971;
    resultado[52] = 0.788010753606722;
    resultado[53] = 0.798635510047293;
    resultado[54] = 0.809016994374947;
    resultado[55] = 0.819152044288992;
    resultado[56] = 0.829037572555042;
    resultado[57] = 0.838670567945424;
    resultado[58] = 0.848048096156426;
    resultado[59] = 0.857167300702112;
    resultado[60] = 0.866025403784439;
    resultado[61] = 0.874619707139396;
    resultado[62] = 0.882947592858927;
    resultado[63] = 0.891006524188368;
    resultado[64] = 0.898794046299167;
    resultado[65] = 0.906307787036650;
    resultado[66] = 0.913545457642601;
    resultado[67] = 0.920504853452440;
    resultado[68] = 0.927183854566787;
    resultado[69] = 0.933580426497202;
    resultado[70] = 0.939692620785908;
    resultado[71] = 0.945518575599317;
    resultado[72] = 0.951056516295154;
    resultado[73] = 0.956304755963035;
    resultado[74] = 0.961261695938319;
    resultado[75] = 0.965925826289068;
    resultado[76] = 0.970295726275996;
    resultado[77] = 0.974370064785235;
    resultado[78] = 0.978147600733806;
    resultado[79] = 0.981627183447664;
    resultado[80] = 0.984807753012208;
    resultado[81] = 0.987688340595138;
    resultado[82] = 0.990268068741570;
    resultado[83] = 0.992546151641322;
    resultado[84] = 0.994521895368273;
    resultado[85] = 0.996194698091746;
    resultado[86] = 0.997564050259824;
    resultado[87] = 0.998629534754574;
    resultado[88] = 0.999390827019096;
    resultado[89] = 0.999847695156391;
    resultado[90] = 1.000000000000000;

    for (int i=0; i<91; i++){
        Q1_14[i]=convertirAQ14(resultado[i]);
    }

    cout << "Vector convertido a Q1.14:" << endl;

    for (int i = 0; i < 91; i++) {
        cout << Q1_14[i] << endl;
    }

    cout<<endl<<endl<<endl;

    cout<<"TABLA_SENO"<<endl;
    for (int i=0; i<91; i++){
        cout<<"\t.FILL #"<<Q1_14[i]<<" ; Resultado de seno("<<i<<")"<<endl;
    }

    return 0;
}